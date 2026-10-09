import logging
from time import perf_counter

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Registra o método, caminho, status e duração de cada requisição HTTP."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        # Este middleware só registra requisições HTTP.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started_at = perf_counter()
        method = scope["method"]
        path = scope["path"]
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)

        except Exception:
            duration_ms = round(
                (perf_counter() - started_at) * 1000,
                2,
            )

            logger.exception(
                "Falha ao processar requisição HTTP.",
                extra={
                    "event": "http_request_failed",
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            raise

        else:
            duration_ms = round(
                (perf_counter() - started_at) * 1000,
                2,
            )

            log_level = (
                logging.WARNING
                if status_code >= 400
                else logging.INFO
            )

            logger.log(
                log_level,
                "Requisição HTTP concluída.",
                extra={
                    "event": "http_request_completed",
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )