# ABOUTME: Stage 3 contract of the autocomplete service: selections raise popularity asynchronously
# ABOUTME: through a Redis queue, and cached suggestions are served while PostgreSQL is stopped.
from typing import Any

import httpx
import pytest

from contract_tests.helpers import (
    compose,
    eventually,
    require,
    stopped_service,
    unique_suffix,
    wait_until_healthy,
)

POPULARITY_DEADLINE = 5.0


def prefix() -> str:
    return "zq" + unique_suffix()


def load(client: httpx.Client, phrases: list[dict[str, Any]]) -> None:
    resp = client.put("/phrases", json={"phrases": phrases})
    require(resp.status_code == 200, f"PUT /phrases: ожидали 200, получили {resp.status_code}.")


def suggestions(client: httpx.Client, q: str) -> list[dict[str, Any]] | None:
    resp = client.get("/suggest", params={"q": q})
    if resp.status_code != 200:
        return None
    result: list[dict[str, Any]] = resp.json().get("suggestions", [])
    return result


def test_query_accepted(client: httpx.Client) -> None:
    p = prefix()
    load(client, [{"text": f"{p} known", "weight": 1}])
    resp = client.post("/queries", json={"text": f"{p} known"})
    require(
        resp.status_code == 202 and resp.content == b"",
        f"POST /queries: ожидали 202 с пустым телом, получили {resp.status_code}: "
        f"{resp.text[:200]}",
    )


def test_unknown_phrase_is_ignored(client: httpx.Client) -> None:
    resp = client.post("/queries", json={"text": f"{prefix()} never loaded"})
    require(
        resp.status_code == 202,
        f"POST /queries с неизвестной фразой: ожидали 202 (выбор игнорируется), получили "
        f"{resp.status_code}.",
    )


@pytest.mark.parametrize("payload", [{"text": ""}, {"text": "   "}, {}])
def test_query_rejects_invalid(client: httpx.Client, payload: dict[str, Any]) -> None:
    resp = client.post("/queries", json=payload)
    require(
        resp.status_code == 422,
        f"POST /queries с телом {payload}: ожидали 422, получили {resp.status_code}.",
    )


def test_selections_raise_popularity(client: httpx.Client) -> None:
    p = prefix()
    load(client, [{"text": f"{p} alpha", "weight": 5}, {"text": f"{p} beta", "weight": 1}])
    before = suggestions(client, p)
    require(
        before is not None and [s.get("text") for s in before] == [f"{p} alpha", f"{p} beta"],
        f"До выборов ждали порядок alpha (5), beta (1), получили {before}.",
    )
    for _ in range(10):
        resp = client.post("/queries", json={"text": f"{p} beta"})
        require(
            resp.status_code == 202, f"POST /queries: ожидали 202, получили {resp.status_code}."
        )
    want = [{"text": f"{p} beta", "weight": 11}, {"text": f"{p} alpha", "weight": 5}]
    require(
        eventually(lambda: suggestions(client, p) == want, POPULARITY_DEADLINE),
        f"После 10 выборов beta за {POPULARITY_DEADLINE:.0f} с ждали {want}, получили "
        f"{suggestions(client, p)}. Итоговый вес = weight + число выборов. Проверьте, что воркер "
        "запущен и что кэш подсказок не отдаёт устаревший ответ.",
    )


@pytest.mark.restarts_containers
def test_suggest_without_database(client: httpx.Client) -> None:
    p = prefix()
    load(
        client, [{"text": f"{p} cached one", "weight": 3}, {"text": f"{p} cached two", "weight": 2}]
    )
    first = suggestions(client, p)
    require(bool(first), f"GET /suggest?q={p}: ждали две подсказки, получили {first}.")
    # Перезапуск app стирает кэш внутри процесса: пройти тест можно только с Redis.
    compose("restart", "app")
    wait_until_healthy(client)
    with stopped_service(client, "db"):
        resp = client.get("/suggest", params={"q": p})
    again = resp.json().get("suggestions") if resp.status_code == 200 else None
    require(
        again == first,
        f"При остановленном PostgreSQL (docker compose stop db) GET /suggest?q={p} вернул "
        f"HTTP {resp.status_code} и {again} вместо {first}. Ответ на уже запрошенный префикс "
        "должен отдаваться из Redis.",
    )
