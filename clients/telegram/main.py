import logging

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler
from telegram.request import HTTPXRequest

from clients.telegram.api_client import ElectionAPIClient
from clients.telegram.handlers import (
    ajuda,
    definir_turno,
    presidente,
    start,
)
from clients.telegram.settings import get_settings
from eleicoes_api.core.logging_config import configure_logging

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Inicializa o cliente HTTP e registra os comandos."""

    settings = get_settings()

    application.bot_data["api_client"] = ElectionAPIClient(
        base_url=settings.api_base_url,
        timeout=settings.api_timeout_seconds,
    )

    await application.bot.set_my_commands(
        [
            BotCommand("start", "Iniciar o bot"),
            BotCommand("ajuda", "Ver os comandos disponíveis"),
            BotCommand("turno", "Selecionar o turno presidencial"),
            BotCommand("presidente", "Resultados por UF ou candidato"),
        ]
    )

    logger.info(
        "Bot Telegram inicializado.",
        extra={"event": "telegram_bot_started"},
    )


async def post_shutdown(application: Application) -> None:
    """Fecha o cliente HTTP ao encerrar o bot."""

    client = application.bot_data.pop("api_client", None)

    if isinstance(client, ElectionAPIClient):
        await client.close()

    logger.info(
        "Bot Telegram encerrado.",
        extra={"event": "telegram_bot_stopped"},
    )


def main() -> None:
    """Configura e executa o bot usando long polling."""

    settings = get_settings()
    configure_logging(settings.environment)

    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    telegram_request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=15.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=10.0,
    )

    polling_request = HTTPXRequest(
        connection_pool_size=2,
        connect_timeout=15.0,
        read_timeout=40.0,
        write_timeout=30.0,
        pool_timeout=10.0,
    )

    application = (
        Application.builder()
        .token(settings.telegram_bot_token.get_secret_value())
        .request(telegram_request)
        .get_updates_request(polling_request)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ajuda", ajuda))
    application.add_handler(CommandHandler("turno", definir_turno))
    application.add_handler(CommandHandler("presidente", presidente))

    logger.info(
        "Iniciando o polling do Telegram.",
        extra={"event": "telegram_polling_starting"},
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()