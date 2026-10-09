import logging

import httpx
import pytest

import eleicoes_api.infrastructure.tse.client as tse_client_module
from eleicoes_api.domain.errors import (
    ElectionDataUnavailableError,
    ElectionResourceNotFoundError,
)
from eleicoes_api.infrastructure.tse.client import TSEClient


LOGGER_NAME = "eleicoes_api.infrastructure.tse.client"


def create_client(
    monkeypatch,
    handler,
    **client_kwargs,
) -> TSEClient:
    """Cria um cliente HTTP simulado, sem acessar a internet."""
    original_async_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def mock_async_client(**kwargs):
        return original_async_client(
            transport=transport,
            **kwargs,
        )

    monkeypatch.setattr(
        tse_client_module.httpx,
        "AsyncClient",
        mock_async_client,
    )

    return TSEClient(**client_kwargs)


@pytest.mark.asyncio
async def test_get_json_success(monkeypatch, caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "ok"},
            request=request,
        )

    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    client = create_client(monkeypatch, handler)

    try:
        result = await client.get_json(
            "https://example.com/resultado.json"
        )

        assert result == {"status": "ok"}

        records = [
            record
            for record in caplog.records
            if getattr(record, "event", None)
            == "tse_request_completed"
        ]

        assert len(records) == 1
        assert records[0].status_code == 200
        assert records[0].duration_ms >= 0
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_json_http_error(monkeypatch, caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            request=request,
        )

    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    client = create_client(monkeypatch, handler)

    try:
        with pytest.raises(
            ElectionResourceNotFoundError,
            match="Recurso não encontrado no TSE",
        ):
            await client.get_json(
                "https://example.com/inexistente.json"
            )

        records = [
            record
            for record in caplog.records
            if getattr(record, "event", None)
            == "tse_request_failed"
        ]

        assert len(records) == 1
        assert records[0].status_code == 404
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_json_connection_error(monkeypatch, caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "connection failed",
            request=request,
        )

    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    client = create_client(monkeypatch, handler)

    try:
        with pytest.raises(
            ElectionDataUnavailableError,
            match="Falha de comunicação com o TSE",
        ):
            await client.get_json(
                "https://example.com/resultado.json"
            )

        records = [
            record
            for record in caplog.records
            if getattr(record, "event", None)
            == "tse_request_failed"
        ]

        assert len(records) == 1
        assert records[0].error_type == "ConnectError"
        assert records[0].duration_ms >= 0
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_json_invalid_response(monkeypatch, caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content="isto não é um JSON válido",
            request=request,
        )

    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    client = create_client(monkeypatch, handler)

    try:
        with pytest.raises(
            ElectionDataUnavailableError,
            match="JSON inválido",
        ):
            await client.get_json(
                "https://example.com/resultado.json"
            )

        records = [
            record
            for record in caplog.records
            if getattr(record, "event", None)
            == "tse_invalid_json"
        ]

        assert len(records) == 1
        assert records[0].status_code == 200
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_json_uses_cache(monkeypatch, caplog):
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        return httpx.Response(
            200,
            json={"votes": 1500},
            request=request,
        )

    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)

    client = create_client(
        monkeypatch,
        handler,
        cache_ttl=30,
    )

    try:
        url = "https://example.com/resultado.json"

        first_result = await client.get_json(url)
        second_result = await client.get_json(url)

        assert first_result == {"votes": 1500}
        assert second_result == {"votes": 1500}

        # Duas consultas devem produzir apenas uma requisição HTTP.
        assert request_count == 1

        cache_hits = [
            record
            for record in caplog.records
            if getattr(record, "event", None) == "tse_cache_hit"
        ]

        assert len(cache_hits) == 1
    finally:
        await client.close()