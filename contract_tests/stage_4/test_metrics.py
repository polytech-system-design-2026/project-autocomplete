# ABOUTME: Stage 4 metrics of the autocomplete service: HTTP counters and histogram with route
# ABOUTME: templates (no raw paths), and the business metric suggest_empty_total.
import httpx

from contract_tests.helpers import metric_samples, metric_sum, require, unique_suffix


def test_http_requests_total_counts_requests(client: httpx.Client) -> None:
    before = metric_sum(
        metric_samples(client), "http_requests_total", method="GET", path="/suggest"
    )
    for _ in range(5):
        client.get("/suggest", params={"q": "zq" + unique_suffix()})
    after = metric_sum(metric_samples(client), "http_requests_total", method="GET", path="/suggest")
    require(
        after - before >= 5,
        f'После 5 запросов GET /suggest счётчик http_requests_total{{method="GET", '
        f'path="/suggest"}} вырос на {after - before:g}, ждали не меньше 5.',
    )


def test_unknown_paths_do_not_create_series(client: httpx.Client) -> None:
    raw = f"/no/such/page-{unique_suffix()}"
    client.get(raw)
    paths = {
        labels.get("path")
        for name, labels, _ in metric_samples(client)
        if name == "http_requests_total"
    }
    require(
        raw not in paths,
        f"Запрос на несуществующий путь {raw} создал в http_requests_total метку path с сырым "
        "путём. В path — только шаблон маршрута; для запросов мимо маршрутов — одно общее "
        "значение, иначе любой сканер создаст тысячи временных рядов.",
    )


def test_request_duration_histogram(client: httpx.Client) -> None:
    client.get("/health")
    names = {name for name, _, _ in metric_samples(client)}
    require(
        "http_request_duration_seconds_bucket" in names,
        "В /metrics нет гистограммы http_request_duration_seconds (сэмплов *_bucket). "
        "Используйте Histogram из prometheus-client с метками method и path.",
    )


def test_suggest_empty_total_grows(client: httpx.Client) -> None:
    before = metric_sum(metric_samples(client), "suggest_empty_total")
    resp = client.get("/suggest", params={"q": "zq" + unique_suffix()})
    require(resp.status_code == 200, f"GET /suggest: ожидали 200, получили {resp.status_code}.")
    after = metric_sum(metric_samples(client), "suggest_empty_total")
    require(
        after - before >= 1,
        f"После запроса с пустой выдачей suggest_empty_total вырос на {after - before:g}, ждали 1.",
    )
