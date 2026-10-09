import logging
from html import escape
from typing import Any

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from clients.telegram.api_client import (
    ElectionAPIClient,
    ElectionAPIError,
)

logger = logging.getLogger(__name__)


STATE_NAMES = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}


RANK_EMOJIS = {
    1: "🥇",
    2: "🥈",
    3: "🥉",
}


def _get_api_client(
    context: ContextTypes.DEFAULT_TYPE,
) -> ElectionAPIClient:
    """Recupera o cliente HTTP da Eleições API."""

    client = context.application.bot_data.get("api_client")

    if not isinstance(client, ElectionAPIClient):
        raise RuntimeError(
            "O cliente da Eleições API não foi inicializado."
        )

    return client


def _get_selected_turn(
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Obtém o turno escolhido pelo usuário; o padrão é o primeiro."""

    user_data = context.user_data

    if user_data is None:
        return 1

    return user_data.get("turno", 1)


def _format_votes(votes: int) -> str:
    """Formata números com ponto como separador de milhares."""

    return f"{votes:,}".replace(",", ".")


def _format_election_results(
    data: dict[str, Any],
    turn: int = 1,
) -> str:
    """Formata os resultados eleitorais para o Telegram."""

    year = data.get("year", "—")
    office = escape(str(data.get("office", "presidente")).title())
    state = data.get("state")
    candidates = data.get("candidates", [])

    if state:
        state = str(state).upper()
        location = (
            f"{escape(STATE_NAMES.get(state, state))} ({escape(state)})"
        )
    else:
        location = "Brasil"

    lines = [
        "🗳️ <b>RESULTADO ELEITORAL</b>",
        "",
        f"🏛️ <b>Cargo:</b> {office}",
        f"📍 <b>Abrangência:</b> {location}",
        f"📅 <b>Ano:</b> {year}  |  <b>Turno:</b> {turn}º",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "<b>VOTAÇÃO DOS CANDIDATOS</b>",
        "",
    ]

    if not candidates:
        lines.append("Nenhum candidato foi encontrado.")
        return "\n".join(lines)

    for position, candidate in enumerate(candidates, start=1):
        number = escape(str(candidate.get("number", "—")))
        name = escape(
            str(candidate.get("name", "Nome indisponível"))
        )
        party = candidate.get("party")
        votes = int(candidate.get("votes", 0))

        party_text = (
            f" <i>({escape(str(party))})</i>"
            if party
            else ""
        )

        rank = RANK_EMOJIS.get(position, f"<b>{position}.</b>")

        lines.extend(
            [
                f"{rank} <b>{number} — {name}</b>{party_text}",
                f"   🗳️ <b>{_format_votes(votes)}</b> votos",
                "",
            ]
        )

    lines.extend(
        [
            "━━━━━━━━━━━━━━━━━━━━",
            "<i>Fonte: TSE, via Eleições API</i>",
        ]
    )

    return "\n".join(lines)


def _format_candidate_votes(data: dict[str, Any]) -> str:
    """Formata a votação nacional e os votos por UF."""

    name = escape(
        str(data.get("candidate_name", "Candidato não identificado"))
    )
    number = escape(str(data.get("candidate_number", "—")))
    party = data.get("party")
    year = data.get("year", "—")
    turn = int(data.get("turn", 1))
    total_votes = int(data.get("total_votes", 0))
    votes_by_state = data.get("votes_by_state", {})

    party_text = (
        f" <i>({escape(str(party))})</i>"
        if party
        else ""
    )

    lines = [
        "📊 <b>VOTAÇÃO POR ESTADO</b>",
        "",
        f"👤 <b>{name}</b>{party_text}",
        f"🔢 <b>Número:</b> {number}",
        f"📅 <b>Ano:</b> {year}  |  <b>Turno:</b> {turn}º",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "🇧🇷 <b>TOTAL NACIONAL</b>",
        f"🗳️ <b>{_format_votes(total_votes)}</b> votos",
        "",
        "📍 <b>DISTRIBUIÇÃO POR UF</b>",
        "",
    ]

    if not isinstance(votes_by_state, dict) or not votes_by_state:
        lines.append("Não há votos estaduais disponíveis.")
    else:
        sorted_states = sorted(
            votes_by_state.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )

        table_lines = [
            f"{'UF':<4} {'VOTOS':>12}",
            f"{'----':<4} {'------------':>12}",
        ]

        for state, votes in sorted_states:
            votes_text = _format_votes(int(votes))
            table_lines.append(
                f"{str(state).upper():<4} {votes_text:>12}"
            )

        lines.append(
            f"<pre>{escape(chr(10).join(table_lines))}</pre>"
        )

    lines.extend(
        [
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "<i>Fonte: TSE, via Eleições API</i>",
        ]
    )

    return "\n".join(lines)


async def _send_api_error(
    update: Update,
    exc: Exception,
) -> None:
    """Apresenta erros sem expor detalhes técnicos inesperados."""

    message = update.effective_message

    if message is None:
        return

    if isinstance(exc, ElectionAPIError):
        await message.reply_text(
            f"⚠️ {escape(str(exc))}",
            parse_mode=ParseMode.HTML,
        )
        return

    logger.error(
        "Erro inesperado no handler do Telegram.",
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    await message.reply_text(
        "⚠️ Ocorreu um erro inesperado ao consultar os resultados.\n"
        "Tente novamente mais tarde."
    )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Responde ao comando /start."""

    message = update.effective_message

    if message is not None:
        selected_turn = _get_selected_turn(context)

        await message.reply_text(
            "👋 <b>Olá! Bem-vindo ao Eleições Bot.</b>\n\n"
            "🗳️ Consulte os resultados presidenciais por estado "
            "ou a votação de um candidato.\n\n"
            f"⚙️ Seu turno atual: <b>{selected_turn}º turno</b>\n\n"
            "Criado por <b>Rafael Torraca Leandro</b> — <i>github.com/rafael-torraca</i>\n\n"
            "Use /turno 1 ou /turno 2 para alterar sua preferência.\n"
            "Digite /ajuda para ver os comandos.",
            parse_mode=ParseMode.HTML,
        )


async def ajuda(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Apresenta a lista de comandos."""

    message = update.effective_message

    if message is None:
        return

    selected_turn = _get_selected_turn(context)

    help_text = (
        "📚 <b>COMANDOS DISPONÍVEIS</b>\n\n"
        "⚙️ <b>/turno 1</b> ou <b>/turno 2</b>\n"
        "Define o turno usado nas consultas presidenciais.\n"
        f"Turno selecionado: <b>{selected_turn}º</b>\n\n"
        "🗳️ <b>/presidente</b>\n"
        "Lista os candidatos e seus votos no Brasil.\n\n"
        "📍 <b>/presidente MG</b>\n"
        "Mostra os resultados de Minas Gerais.\n"
        "Substitua MG por qualquer UF: SP, RJ, DF, BA etc.\n\n"
        "🔎 <b>/presidente nome do candidato</b>\n"
        "Mostra o total nacional e os votos por estado.\n"
        "Exemplo: <code>/presidente flavio bolsonaro</code>\n\n"
        "ℹ️ <b>/ajuda</b>\n"
        "Mostra esta lista de comandos."
    )

    await message.reply_text(
        help_text,
        parse_mode=ParseMode.HTML,
    )


async def definir_turno(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Define a preferência de turno do usuário do Telegram."""

    message = update.effective_message

    if message is None:
        return

    user_data = context.user_data

    if user_data is None:
        await message.reply_text(
            "Não foi possível salvar sua preferência nesta conversa."
        )
        return

    if not context.args:
        selected_turn = _get_selected_turn(context)

        await message.reply_text(
            f"⚙️ Seu turno presidencial atual é o {selected_turn}º turno.\n\n"
            "Para alterar, use /turno 1 ou /turno 2."
        )
        return

    if len(context.args) != 1 or context.args[0] not in ("1", "2"):
        await message.reply_text(
            "⚠️ Informe um turno válido.\n\n"
            "Use /turno 1 para o primeiro turno ou /turno 2 "
            "para o segundo turno."
        )
        return

    selected_turn = int(context.args[0])
    user_data["turno"] = selected_turn

    await message.reply_text(
        f"✅ Turno presidencial definido: {selected_turn}º turno.\n\n"
        "Essa preferência será usada nas próximas consultas "
        "com /presidente, até você alterá-la."
    )


async def presidente(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Sem argumentos: consulta todos os candidatos no Brasil.
    Com uma UF: consulta os resultados daquele estado.
    Com nome ou número: consulta a votação do candidato por UF.
    """

    message = update.effective_message

    if message is None:
        return

    selected_turn = _get_selected_turn(context)

    try:
        client = _get_api_client(context)
        args = context.args

        if not args:
            data = await client.get_election_results(
                office="presidente",
                turn=selected_turn,
            )

            response_text = _format_election_results(
                data,
                turn=selected_turn,
            )

        elif len(args) == 1 and args[0].upper() in STATE_NAMES:
            state = args[0].upper()

            data = await client.get_election_results(
                office="presidente",
                state=state,
                turn=selected_turn,
            )

            response_text = _format_election_results(
                data,
                turn=selected_turn,
            )

        else:
            candidate = " ".join(args).strip()

            data = await client.get_candidate_votes_by_state(
                candidate=candidate,
                office="presidente",
                turn=selected_turn,
            )

            response_text = _format_candidate_votes(data)

        await message.reply_text(
            response_text,
            parse_mode=ParseMode.HTML,
        )

    except Exception as exc:
        await _send_api_error(update, exc)