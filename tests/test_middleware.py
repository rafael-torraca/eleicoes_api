import logging

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from eleicoes_api.api.middleware import RequestLoggingMiddleware


LOGGER_NAME = "eleicoes_api.api.middleware"


@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/unavailable")
    def unavailable():
        raise HTTPException(
            status_code=503,
            detail="Serviço temporariamente indisponível",
        )

    with TestClient(app) as test_client:
        yield test_client


def test_logs_successful_request(client, caplog):
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    records = [
        record
        for record in caplog.records
        if getattr(record, "event", None)
        == "http_request_completed"
    ]

    assert len(records) == 1

    record = records[0]

    assert record.method == "GET"
    assert record.path == "/health"
    assert record.status_code == 200
    assert record.duration_ms >= 0


def test_logs_http_error_response(client, caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)

    response = client.get("/unavailable")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Serviço temporariamente indisponível"
    )

    records = [
        record
        for record in caplog.records
        if getattr(record, "event", None)
        == "http_request_completed"
    ]

    assert len(records) == 1

    record = records[0]

    assert record.method == "GET"
    assert record.path == "/unavailable"
    assert record.status_code == 503
    assert record.duration_ms >= 0
    assert record.levelno == logging.WARNING
