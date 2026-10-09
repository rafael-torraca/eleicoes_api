import pytest
from fastapi.testclient import TestClient

from eleicoes_api.api.dependencies import get_election_service
from eleicoes_api.core.config import get_settings
from eleicoes_api.domain.errors import (
    CandidateNotFoundError,
    ElectionDataUnavailableError,
)
from eleicoes_api.domain.schemas import (
    CandidateResult,
    CandidateVotesByState,
    ElectionResults,
)
from eleicoes_api.main import create_app


class FakeElectionService:
    """Simula o serviço eleitoral para testar a API."""

    def __init__(self) -> None:
        self.last_query = {}
        self.error_to_raise: Exception | None = None

    async def get_results(
        self,
        year: int,
        office: str,
        state: str | None = None,
        turn: int = 1,
    ) -> ElectionResults:
        if self.error_to_raise:
            raise self.error_to_raise

        self.last_query = {
            "year": year,
            "office": office,
            "state": state,
            "turn": turn,
        }

        return ElectionResults(
            year=year,
            office=office,
            state=state,
            candidates=[
                CandidateResult(
                    number=22,
                    name="CANDIDATO TESTE",
                    party="PL",
                    votes=1500,
                )
            ],
        )

    async def get_candidate_votes_by_state(
        self,
        year: int,
        office: str,
        candidate_name: str,
        turn: int = 1,
    ) -> CandidateVotesByState:
        if self.error_to_raise:
            raise self.error_to_raise

        self.last_query = {
            "year": year,
            "office": office,
            "candidate_name": candidate_name,
            "turn": turn,
        }

        return CandidateVotesByState(
            year=year,
            office=office,
            turn=turn,
            candidate_number=22,
            candidate_name="CANDIDATO TESTE",
            party="PL",
            total_votes=4000,
            votes_by_state={
                "MG": 1500,
                "SP": 2500,
            },
        )


@pytest.fixture
def api_client():
    app = create_app()
    service = FakeElectionService()

    app.dependency_overrides[get_election_service] = lambda: service

    try:
        with TestClient(app) as client:
            yield client, service
    finally:
        app.dependency_overrides.clear()


def test_health_endpoint(api_client):
    client, _ = api_client

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_results_default_year_and_second_turn(api_client):
    client, service = api_client

    response = client.get(
        "/v1/eleicoes/cargos/presidente/resultados",
        params={"uf": "MG", "turno": 2},
    )

    assert response.status_code == 200
    assert response.json()["year"] == get_settings().default_election_year
    assert response.json()["state"] == "MG"
    assert service.last_query["turn"] == 2


def test_invalid_turn_returns_422(api_client):
    client, _ = api_client

    response = client.get(
        "/v1/eleicoes/cargos/presidente/resultados",
        params={"turno": 3},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
    assert response.json()["message"] == (
        "Os parâmetros enviados são inválidos."
    )
    assert response.json()["details"]


def test_candidate_votes_by_state(api_client):
    client, service = api_client

    response = client.get(
        "/v1/eleicoes/cargos/presidente/votos-por-uf",
        params={
            "candidato": "22",
            "ano": 2026,
            "turno": 2,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["year"] == 2026
    assert data["office"] == "presidente"
    assert data["turn"] == 2
    assert data["candidate_number"] == 22
    assert data["candidate_name"] == "CANDIDATO TESTE"
    assert data["party"] == "PL"
    assert data["total_votes"] == 4000
    assert data["votes_by_state"] == {
        "MG": 1500,
        "SP": 2500,
    }

    assert service.last_query["candidate_name"] == "22"
    assert service.last_query["turn"] == 2


def test_candidate_not_found_has_standardized_response(api_client):
    client, service = api_client

    service.error_to_raise = CandidateNotFoundError(
        "Candidato não encontrado: 999"
    )

    response = client.get(
        "/v1/eleicoes/cargos/presidente/votos-por-uf",
        params={"candidato": "999"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": "candidate_not_found",
        "message": "Candidato não encontrado: 999",
    }


def test_election_data_unavailable_has_standardized_response(api_client):
    client, service = api_client

    service.error_to_raise = ElectionDataUnavailableError(
        "Dados eleitorais indisponíveis."
    )

    response = client.get(
        "/v1/eleicoes/cargos/presidente/resultados",
    )

    assert response.status_code == 503
    assert response.json() == {
        "error": "election_data_unavailable",
        "message": "Dados eleitorais indisponíveis.",
    }


def test_invalid_query_has_standardized_response(api_client):
    client, _ = api_client

    response = client.get(
        "/v1/eleicoes/cargos/presidente/resultados",
        params={"uf": "MG", "ano": "invalido"},
    )

    assert response.status_code == 422

    data = response.json()

    assert data["error"] == "validation_error"
    assert data["message"] == (
        "Os parâmetros enviados são inválidos."
    )
    assert any(
        detail["field"] == "query.ano"
        for detail in data["details"]
    )