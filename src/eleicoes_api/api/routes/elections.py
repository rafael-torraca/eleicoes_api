from fastapi import APIRouter, Query

from eleicoes_api.api.dependencies import ElectionServiceDep
from eleicoes_api.core.config import get_settings
from eleicoes_api.domain.schemas import (
    CandidateVotesByState,
    ElectionResults,
)

router = APIRouter(prefix="/v1/eleicoes", tags=["Eleições"])


@router.get(
    "/cargos/{office}/resultados",
    response_model=ElectionResults,
)
async def get_election_results(
    office: str,
    service: ElectionServiceDep,
    ano: int | None = Query(default=None, ge=1900),
    uf: str | None = Query(default=None, min_length=2, max_length=2),
    turno: int = Query(default=1, ge=1, le=2),
) -> ElectionResults:
    settings = get_settings()
    year = ano if ano is not None else settings.default_election_year

    return await service.get_results(
        year=year,
        office=office,
        state=uf,
        turn=turno,
    )


@router.get(
    "/cargos/{office}/votos-por-uf",
    response_model=CandidateVotesByState,
)
async def get_candidate_votes_by_state(
    office: str,
    service: ElectionServiceDep,
    candidato: str = Query(min_length=1),
    ano: int | None = Query(default=None, ge=1900),
    turno: int = Query(default=1, ge=1, le=2),
) -> CandidateVotesByState:
    settings = get_settings()
    year = ano if ano is not None else settings.default_election_year

    return await service.get_candidate_votes_by_state(
        year=year,
        office=office,
        candidate_name=candidato,
        turn=turno,
    )