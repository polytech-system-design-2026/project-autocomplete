# ABOUTME: Stage 2 contract of the autocomplete service: dictionary load, phrases, suggestions.
# ABOUTME: Every test uses its own unique prefix, so tests do not see each other's phrases.
import time
from typing import Any

import httpx
import pytest

from contract_tests.helpers import compose, require, unique_suffix, wait_until_healthy


def prefix() -> str:
    """Уникальное начало фраз теста: латиница, чтобы не зависеть от сортировки кириллицы."""
    return "zq" + unique_suffix()


def load(client: httpx.Client, phrases: list[dict[str, Any]]) -> dict[str, Any]:
    resp = client.put("/phrases", json={"phrases": phrases}, timeout=60)
    require(
        resp.status_code == 200,
        f"PUT /phrases: ожидали 200, получили {resp.status_code}: {resp.text[:300]}",
    )
    body: dict[str, Any] = resp.json()
    return body


def suggest(client: httpx.Client, q: str, limit: int | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"q": q}
    if limit is not None:
        params["limit"] = limit
    resp = client.get("/suggest", params=params)
    require(
        resp.status_code == 200,
        f"GET /suggest?q={q}: ожидали 200, получили {resp.status_code}: {resp.text[:300]}",
    )
    suggestions: list[dict[str, Any]] = resp.json().get("suggestions")
    require(
        isinstance(suggestions, list),
        f"GET /suggest?q={q}: в ответе нет списка suggestions: {resp.text[:300]}",
    )
    return suggestions


def texts(suggestions: list[dict[str, Any]]) -> list[str]:
    return [s.get("text", "") for s in suggestions]


def test_load_and_suggest(client: httpx.Client) -> None:
    p = prefix()
    body = load(client, [{"text": f"{p} alpha", "weight": 10}, {"text": f"{p} beta", "weight": 3}])
    require(
        body == {"loaded": 2},
        f'PUT /phrases с двумя фразами: ждали {{"loaded": 2}}, получили {body}.',
    )
    resp = client.get("/suggest", params={"q": p})
    require(resp.status_code == 200, f"GET /suggest: ожидали 200, получили {resp.status_code}.")
    data = resp.json()
    require(
        data.get("query") == p,
        f"GET /suggest?q={p}: поле query = {data.get('query')!r}, ждали {p!r}.",
    )
    require(
        data.get("suggestions")
        == [
            {"text": f"{p} alpha", "weight": 10},
            {"text": f"{p} beta", "weight": 3},
        ],
        f"GET /suggest?q={p}: ждали две фразы по убыванию веса, "
        f"получили {data.get('suggestions')}.",
    )


def test_load_default_weight_is_one(client: httpx.Client) -> None:
    p = prefix()
    load(client, [{"text": f"{p} plain"}])
    got = suggest(client, p)
    require(
        got == [{"text": f"{p} plain", "weight": 1}],
        f"Фраза без weight должна получить вес 1, получили {got}.",
    )


def test_load_upserts_existing(client: httpx.Client) -> None:
    p = prefix()
    load(client, [{"text": f"{p} same", "weight": 1}])
    load(client, [{"text": f"{p} same", "weight": 7}])
    got = suggest(client, p)
    require(
        got == [{"text": f"{p} same", "weight": 7}],
        f"Повторный PUT /phrases с той же фразой должен обновить вес, а не добавить дубль: {got}.",
    )


def test_load_counts_unique_normalized(client: httpx.Client) -> None:
    p = prefix()
    body = load(
        client, [{"text": f"{p} dup", "weight": 1}, {"text": f"  {p.upper()}   DUP ", "weight": 2}]
    )
    require(
        body == {"loaded": 1},
        f"Две фразы, одинаковые после нормализации, — это одна фраза: ждали {{'loaded': 1}}, "
        f"получили {body}.",
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"phrases": []},
        {"phrases": [{"text": "", "weight": 1}]},
        {"phrases": [{"text": "   ", "weight": 1}]},
        {"phrases": [{"text": "negative weight", "weight": -1}]},
        {},
    ],
)
def test_load_rejects_invalid(client: httpx.Client, payload: dict[str, Any]) -> None:
    resp = client.put("/phrases", json=payload)
    require(
        resp.status_code == 422,
        f"PUT /phrases с телом {payload}: ожидали 422, получили {resp.status_code}.",
    )


def test_add_phrase(client: httpx.Client) -> None:
    p = prefix()
    resp = client.post("/phrases", json={"text": f"  {p.upper()}   New  Phrase ", "weight": 4})
    require(
        resp.status_code == 201,
        f"POST /phrases: ожидали 201, получили {resp.status_code}: {resp.text[:300]}",
    )
    body = resp.json()
    require(
        isinstance(body.get("id"), int)
        and body.get("text") == f"{p} new phrase"
        and body.get("weight") == 4,
        f"POST /phrases: ждали id (число), нормализованный text {p + ' new phrase'!r} и weight 4, "
        f"получили {body}.",
    )
    require(
        texts(suggest(client, p)) == [f"{p} new phrase"],
        "Добавленная фраза не появилась в /suggest.",
    )


def test_add_duplicate_conflict(client: httpx.Client) -> None:
    p = prefix()
    first = client.post("/phrases", json={"text": f"{p} once", "weight": 1})
    require(first.status_code == 201, f"POST /phrases: ожидали 201, получили {first.status_code}.")
    second = client.post("/phrases", json={"text": f"{p.upper()}  ONCE", "weight": 5})
    require(
        second.status_code == 409,
        f"Повторный POST /phrases той же фразы (в другом регистре): ожидали 409, получили "
        f"{second.status_code}.",
    )


@pytest.mark.parametrize(
    "payload", [{"text": "", "weight": 1}, {"text": "x", "weight": -5}, {"weight": 1}]
)
def test_add_rejects_invalid(client: httpx.Client, payload: dict[str, Any]) -> None:
    resp = client.post("/phrases", json=payload)
    require(
        resp.status_code == 422,
        f"POST /phrases с телом {payload}: ожидали 422, получили {resp.status_code}.",
    )


def test_suggest_normalizes_query(client: httpx.Client) -> None:
    p = prefix()
    load(client, [{"text": f"{p} python tutorial", "weight": 5}])
    resp = client.get("/suggest", params={"q": f"  {p.upper()}   PYTHON "})
    require(resp.status_code == 200, f"GET /suggest: ожидали 200, получили {resp.status_code}.")
    data = resp.json()
    require(
        texts(data.get("suggestions", [])) == [f"{p} python tutorial"],
        f"Запрос в другом регистре и с лишними пробелами должен находить фразу: {data}.",
    )
    require(
        data.get("query") == f"{p} python",
        f"query должен быть нормализован: {data.get('query')!r}.",
    )


def test_only_prefix_matches(client: httpx.Client) -> None:
    p = prefix()
    load(
        client, [{"text": f"{p} apple pie", "weight": 1}, {"text": f"{p} green apple", "weight": 9}]
    )
    got = texts(suggest(client, f"{p} apple"))
    require(
        got == [f"{p} apple pie"],
        f"Выдача содержит фразы, которые не начинаются с префикса: {got}.",
    )


def test_wildcards_are_literal(client: httpx.Client) -> None:
    p = prefix()
    load(
        client,
        [
            {"text": f"{p} 50% off", "weight": 1},
            {"text": f"{p} 50 cents", "weight": 1},
            {"text": f"{p} a_b", "weight": 1},
            {"text": f"{p} axb", "weight": 1},
        ],
    )
    require(
        texts(suggest(client, f"{p} 50%")) == [f"{p} 50% off"],
        "Символ % в запросе должен искаться как обычный символ, а не как шаблон SQL LIKE.",
    )
    require(
        texts(suggest(client, f"{p} a_")) == [f"{p} a_b"],
        "Символ _ в запросе должен искаться как обычный символ, а не как шаблон SQL LIKE.",
    )


def test_ties_sorted_by_text(client: httpx.Client) -> None:
    p = prefix()
    load(
        client,
        [
            {"text": f"{p} cherry", "weight": 5},
            {"text": f"{p} apple", "weight": 5},
            {"text": f"{p} banana", "weight": 5},
            {"text": f"{p} top", "weight": 6},
        ],
    )
    got = texts(suggest(client, p))
    want = [f"{p} top", f"{p} apple", f"{p} banana", f"{p} cherry"]
    require(
        got == want,
        f"Порядок: по убыванию веса, при равном весе по тексту. Ждали {want}, получили {got}.",
    )


def test_limit(client: httpx.Client) -> None:
    p = prefix()
    load(client, [{"text": f"{p} item {i:02d}", "weight": i} for i in range(15)])
    require(len(suggest(client, p)) == 10, "Без limit выдача должна содержать 10 подсказок.")
    got = texts(suggest(client, p, limit=3))
    want = [f"{p} item 14", f"{p} item 13", f"{p} item 12"]
    require(got == want, f"limit=3: ждали {want}, получили {got}.")


def test_empty_result_is_200(client: httpx.Client) -> None:
    got = suggest(client, prefix())
    require(got == [], f"Префикс без совпадений: ждали 200 и пустой список, получили {got}.")


@pytest.mark.parametrize(
    "params", [{"q": ""}, {"q": "   "}, {}, {"q": "a", "limit": 0}, {"q": "a", "limit": 51}]
)
def test_suggest_rejects_invalid(client: httpx.Client, params: dict[str, Any]) -> None:
    resp = client.get("/suggest", params=params)
    require(
        resp.status_code == 422,
        f"GET /suggest с параметрами {params}: ожидали 422, получили {resp.status_code}.",
    )


def test_large_dictionary(client: httpx.Client) -> None:
    p = prefix()
    phrases = [{"text": f"{p} word {i:05d}", "weight": i % 100} for i in range(5000)]
    started = time.monotonic()
    body = load(client, phrases)
    load_seconds = time.monotonic() - started
    require(
        body == {"loaded": 5000},
        f"PUT /phrases с 5 000 фраз: ждали {{'loaded': 5000}}, получили {body}.",
    )
    require(load_seconds < 20, f"Загрузка 5 000 фраз заняла {load_seconds:.1f} с, нужно меньше 20.")
    started = time.monotonic()
    got = suggest(client, f"{p} word 012", limit=5)
    search_seconds = time.monotonic() - started
    require(len(got) == 5, f"Поиск по словарю из 5 000 фраз вернул {len(got)} подсказок вместо 5.")
    require(
        search_seconds < 1,
        f"Поиск по словарю из 5 000 фраз занял {search_seconds:.2f} с, нужно меньше 1.",
    )


@pytest.mark.restarts_containers
def test_dictionary_survives_app_restart(client: httpx.Client) -> None:
    p = prefix()
    load(client, [{"text": f"{p} persistent", "weight": 2}])
    compose("restart", "app")
    wait_until_healthy(client)
    got = suggest(client, p)
    require(
        got == [{"text": f"{p} persistent", "weight": 2}],
        f"После docker compose restart app фраза пропала: {got}. Словарь должен храниться в "
        "PostgreSQL, а не в памяти процесса.",
    )
