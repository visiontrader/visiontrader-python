"""Internal HTTP helpers."""

from __future__ import annotations

import os
from typing import Any

import httpx

from visiontrader.exceptions import ApiError, ValidationError

DEFAULT_BASE_URL = "http://localhost:5259"
ENV_BASE_URL = "VT_API_BASE_URL"


class HttpClient:
    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        resolved = (base_url or os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url=resolved, timeout=timeout)

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

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._client.get(path, params=params)
        return _parse_response(response)


def _parse_response(response: httpx.Response) -> dict[str, Any]:
    try:
        body: dict[str, Any] = response.json()
    except ValueError as exc:
        raise ApiError(
            f"Non-JSON response (HTTP {response.status_code})",
            status_code=response.status_code,
        ) from exc

    if response.status_code == 400:
        message = str(body.get("error") or body.get("title") or "Bad request")
        raise ValidationError(message, status_code=400)

    if response.status_code >= 500:
        detail = body.get("detail") or body.get("error") or response.reason_phrase
        raise ApiError(str(detail), status_code=response.status_code)

    if response.status_code >= 400:
        message = str(body.get("error") or body.get("title") or response.reason_phrase)
        raise ApiError(message, status_code=response.status_code)

    response.raise_for_status()
    return body


def unwrap_data(body: dict[str, Any]) -> Any:
    if "data" not in body:
        raise ApiError("Response missing 'data' field")
    return body["data"]
