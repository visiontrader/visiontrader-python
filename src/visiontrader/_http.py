"""Internal HTTP helpers."""

from __future__ import annotations

import os
from typing import Any

import httpx

from visiontrader.exceptions import ApiError, ValidationError

DEFAULT_BASE_URL = 'http://localhost:5259'
ENV_BASE_URL = 'VT_API_BASE_URL'
DEFAULT_TIMEOUT = 240.0


def _http_timeout(seconds: float) -> httpx.Timeout:
    return httpx.Timeout(seconds)


class HttpClient:
    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.Client | None = None,
    ) -> None:
        resolved = (base_url or os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL).rstrip('/')
        self._base_url = resolved
        self._timeout = _http_timeout(timeout)
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url=resolved, timeout=self._timeout)

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def client(self) -> httpx.Client:
        return self._client

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_json(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = self._client.get(path, params=params, headers=headers, timeout=self._timeout)
        return _parse_response(response)


def _response_preview(response: httpx.Response, *, limit: int = 300) -> str:
    text = response.text.strip()
    if not text:
        return '(empty body)'
    if len(text) <= limit:
        return text
    return f'{text[:limit]}...'


def _format_error_message(body: dict[str, Any], *, fallback: str) -> str:
    error = _response_error(body)
    detail = body.get('message') or body.get('title') or body.get('detail')
    detail_text = str(detail).strip() if detail is not None else ''
    if error and detail_text and error != detail_text:
        return f'{error}: {detail_text}'
    if detail_text:
        return detail_text
    if error:
        return error
    return fallback


def _raise_api_error(
    body: dict[str, Any],
    *,
    status_code: int,
    fallback: str,
    exception_type: type[ApiError] = ApiError,
) -> None:
    raise exception_type(
        _format_error_message(body, fallback=fallback),
        status_code=status_code,
        code=_response_code(body),
        error_code=_response_error(body),
    )


def _parse_response(response: httpx.Response) -> dict[str, Any]:
    try:
        body: dict[str, Any] = response.json()
    except ValueError as exc:
        request = response.request
        raise ApiError(
            f'Non-JSON response (HTTP {response.status_code}) from '
            f'{request.method} {request.url}: {_response_preview(response)}',
            status_code=response.status_code,
        ) from exc

    if response.status_code == 400:
        _raise_api_error(
            body,
            status_code=400,
            fallback='Bad request',
            exception_type=ValidationError,
        )

    if response.status_code >= 500:
        _raise_api_error(
            body,
            status_code=response.status_code,
            fallback=str(response.reason_phrase),
        )

    if response.status_code >= 400:
        _raise_api_error(
            body,
            status_code=response.status_code,
            fallback=str(response.reason_phrase),
        )

    response.raise_for_status()
    return body


def _response_code(body: dict[str, Any]) -> int | None:
    code = body.get('code')
    return int(code) if code is not None else None


def _response_error(body: dict[str, Any]) -> str | None:
    error = body.get('error')
    if error is None:
        return None
    text = str(error).strip()
    return text or None


def unwrap_data(body: dict[str, Any]) -> Any:
    if 'data' not in body:
        raise ApiError("Response missing 'data' field")

    error = _response_error(body)
    if error is not None:
        raise ApiError(
            _format_error_message(body, fallback=error),
            code=_response_code(body),
            error_code=error,
        )

    return body['data']
