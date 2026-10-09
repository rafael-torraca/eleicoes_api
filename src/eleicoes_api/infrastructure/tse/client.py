import logging
import time
from urllib.parse import urlsplit

import httpx

from eleicoes_api.domain.errors import (
    ElectionDataUnavailableError,
    ElectionResourceNotFoundError,
)

logger = logging.getLogger(__name__)


class TSEClient:
    def __init__(
        self,
        timeout: float = 15.0,
        cache_ttl: float = 15.0,
        max_cache_entries: int = 512,
    ) -> None:
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "eleicoes-api/0.1.0"},
        )

        self._cache_ttl = cache_ttl
        self._max_cache_entries = max_cache_entries

        # URL -> (instante de expiração, resposta JSON)
        self._cache: dict[str, tuple[float, dict | list]] = {}

    async def get_json(self, url: str) -> dict | list:
        cached = self._cache.get(url)
        now = time.monotonic()
        path = urlsplit(url).path

        if cached is not None:
            expires_at, payload = cached

            if expires_at > now:
                logger.debug(
                    "Cache encontrado.",
                    extra={
                        "event": "tse_cache_hit",
                        "path": path,
                    },
                )
                return payload

            self._cache.pop(url, None)

        logger.debug(
            "Cache não encontrado ou expirado.",
            extra={
                "event": "tse_cache_miss",
                "path": path,
            },
        )

        started_at = time.perf_counter()

        try:
            response = await self._client.get(url)
            response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            duration_ms = round(
                (time.perf_counter() - started_at) * 1000,
                2,
            )

            logger.warning(
                "O TSE respondeu com erro HTTP.",
                extra={
                    "event": "tse_request_failed",
                    "path": path,
                    "status_code": exc.response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            if exc.response.status_code == 404:
                raise ElectionResourceNotFoundError(
                    f"Recurso não encontrado no TSE: {exc.request.url}"
                ) from exc

            raise ElectionDataUnavailableError(
                f"O TSE respondeu com HTTP "
                f"{exc.response.status_code} ao consultar "
                f"{exc.request.url}."
            ) from exc

        except httpx.RequestError as exc:
            duration_ms = round(
                (time.perf_counter() - started_at) * 1000,
                2,
            )

            logger.warning(
                "Falha de comunicação com o TSE.",
                extra={
                    "event": "tse_request_failed",
                    "path": path,
                    "error_type": type(exc).__name__,
                    "duration_ms": duration_ms,
                },
                exc_info=True,
            )

            raise ElectionDataUnavailableError(
                f"Falha de comunicação com o TSE ao consultar "
                f"{exc.request.url}. Erro: {type(exc).__name__}."
            ) from exc

        duration_ms = round(
            (time.perf_counter() - started_at) * 1000,
            2,
        )

        try:
            payload = response.json()

        except ValueError as exc:
            logger.warning(
                "O TSE retornou uma resposta JSON inválida.",
                extra={
                    "event": "tse_invalid_json",
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            raise ElectionDataUnavailableError(
                f"O TSE retornou JSON inválido para {response.url}."
            ) from exc

        if not isinstance(payload, (dict, list)):
            logger.warning(
                "O TSE retornou um formato JSON inesperado.",
                extra={
                    "event": "tse_unexpected_json",
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            raise ElectionDataUnavailableError(
                f"O TSE retornou um formato JSON inesperado "
                f"para {response.url}."
            )

        self._save_cache(url, payload)

        logger.info(
            "Consulta ao TSE concluída.",
            extra={
                "event": "tse_request_completed",
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return payload

    def _save_cache(
        self,
        url: str,
        payload: dict | list,
    ) -> None:
        if self._cache_ttl <= 0 or self._max_cache_entries <= 0:
            return

        while len(self._cache) >= self._max_cache_entries:
            oldest_url = min(
                self._cache,
                key=lambda key: self._cache[key][0],
            )
            self._cache.pop(oldest_url)

        self._cache[url] = (
            time.monotonic() + self._cache_ttl,
            payload,
        )

    async def close(self) -> None:
        self._cache.clear()
        await self._client.aclose()