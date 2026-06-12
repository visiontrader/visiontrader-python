import httpx

from visiontrader._http import DEFAULT_TIMEOUT, HttpClient


def test_default_timeout_is_four_minutes() -> None:
    assert DEFAULT_TIMEOUT == 240.0


def test_get_json_passes_configured_timeout_even_with_external_client() -> None:
    seen: dict[str, httpx.Timeout | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen['timeout'] = request.extensions.get('timeout')
        return httpx.Response(200, json={'data': []})

    transport = httpx.MockTransport(handler)
    external = httpx.Client(transport=transport, timeout=60.0)
    http = HttpClient(client=external, timeout=DEFAULT_TIMEOUT)
    try:
        http.get_json('/exchanges')
    finally:
        http.close()

    timeout = seen['timeout']
    assert timeout is not None
    assert timeout.read == DEFAULT_TIMEOUT
