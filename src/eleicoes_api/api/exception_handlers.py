from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from eleicoes_api.domain.errors import (
    CandidateNotFoundError,
    ElectionDataUnavailableError,
    ElectionError,
)


async def candidate_not_found_handler(
    request: Request,
    exc: CandidateNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": "candidate_not_found",
            "message": str(exc),
        },
    )


async def election_data_unavailable_handler(
    request: Request,
    exc: ElectionDataUnavailableError,
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": "election_data_unavailable",
            "message": str(exc),
        },
    )


async def election_error_handler(
    request: Request,
    exc: ElectionError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": "election_error",
            "message": str(exc),
        },
    )


async def value_error_handler(
    request: Request,
    exc: ValueError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_request",
            "message": str(exc),
        },
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = [
        {
            "field": ".".join(
                str(part) for part in error.get("loc", ())
            ),
            "message": error.get("msg", "Parâmetro inválido."),
            "type": error.get("type", "validation_error"),
        }
        for error in exc.errors()
    ]

    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Os parâmetros enviados são inválidos.",
            "details": details,
        },
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    error_codes = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        422: "validation_error",
        503: "service_unavailable",
    }

    error_code = error_codes.get(
        exc.status_code,
        "http_error",
    )

    message = (
        exc.detail
        if isinstance(exc.detail, str)
        else "A requisição não pôde ser processada."
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_code,
            "message": message,
        },
        headers=exc.headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registra os tratadores globais de erros da aplicação."""

    app.add_exception_handler(
        CandidateNotFoundError,
        candidate_not_found_handler,
    )
    app.add_exception_handler(
        ElectionDataUnavailableError,
        election_data_unavailable_handler,
    )
    app.add_exception_handler(
        ElectionError,
        election_error_handler,
    )
    app.add_exception_handler(
        ValueError,
        value_error_handler,
    )
    app.add_exception_handler(
        RequestValidationError,
        validation_error_handler,
    )
    app.add_exception_handler(
        StarletteHTTPException,
        http_exception_handler,
    )
