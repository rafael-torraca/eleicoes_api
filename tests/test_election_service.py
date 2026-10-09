import pytest

from eleicoes_api.application.election_service import ElectionService
from eleicoes_api.domain.schemas import (
    CandidateVotesByState,
    ElectionResults,
)


class FakeElectionRepository:
    """Repositório simulado para testar o serviço."""

    def __init__(self) -> None:
        self.last_results_query = None
        self.last_candidate_query = None

    async def get_results(
        self,
        year: int,
        office: str,
        state: str | None = None,
        turn: int = 1,
    ) -> ElectionResults:
        self.last_results_query = {
            "year": year,
            "office": office,
            "state": state,
            "turn": turn,
        }

        return ElectionResults(
            year=year,
            office=office,
            state=state,
            candidates=[],
        )

    async def get_candidate_votes_by_state(
        self,
        year: int,
        office: str,
        candidate_name: str,
        turn: int = 1,
    ) -> CandidateVotesByState:
        self.last_candidate_query = {
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
            total_votes=100,
            votes_by_state={"MG": 100},
        )


@pytest.mark.asyncio
async def test_results_normalizes_parameters() -> None:
    repository = FakeElectionRepository()
    service = ElectionService(repository)

    result = await service.get_results(
        year=2026,
        office=" Presidente ",
        state=" mg ",
        turn=2,
    )

    assert result.office == "presidente"
    assert result.state == "MG"

    assert repository.last_results_query == {
        "year": 2026,
        "office": "presidente",
        "state": "MG",
        "turn": 2,
    }


@pytest.mark.asyncio
async def test_results_accepts_national_query() -> None:
    repository = FakeElectionRepository()
    service = ElectionService(repository)

    result = await service.get_results(
        year=2026,
        office="presidente",
    )

    assert result.state is None
    assert repository.last_results_query["state"] is None
    assert repository.last_results_query["turn"] == 1


@pytest.mark.asyncio
async def test_rejects_invalid_year() -> None:
    service = ElectionService(FakeElectionRepository())

    with pytest.raises(ValueError, match="ano da eleição"):
        await service.get_results(
            year=1899,
            office="presidente",
        )


@pytest.mark.asyncio
async def test_rejects_invalid_turn() -> None:
    service = ElectionService(FakeElectionRepository())

    with pytest.raises(ValueError, match="turno deve ser 1 ou 2"):
        await service.get_results(
            year=2026,
            office="presidente",
            turn=3,
        )


@pytest.mark.asyncio
async def test_second_turn_is_limited_to_president() -> None:
    service = ElectionService(FakeElectionRepository())

    with pytest.raises(
        ValueError,
        match="apenas para presidente",
    ):
        await service.get_results(
            year=2026,
            office="governador",
            state="MG",
            turn=2,
        )


@pytest.mark.asyncio
async def test_candidate_query_normalizes_parameters() -> None:
    repository = FakeElectionRepository()
    service = ElectionService(repository)

    result = await service.get_candidate_votes_by_state(
        year=2026,
        office=" Presidente ",
        candidate_name=" 22 ",
        turn=1,
    )

    assert result.candidate_number == 22

    assert repository.last_candidate_query == {
        "year": 2026,
        "office": "presidente",
        "candidate_name": "22",
        "turn": 1,
    }


@pytest.mark.asyncio
async def test_candidate_name_is_required() -> None:
    service = ElectionService(FakeElectionRepository())

    with pytest.raises(
        ValueError,
        match="nome ou número do candidato é obrigatório",
    ):
        await service.get_candidate_votes_by_state(
            year=2026,
            office="presidente",
            candidate_name="   ",
        )
