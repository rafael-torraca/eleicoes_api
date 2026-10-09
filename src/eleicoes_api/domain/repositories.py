from typing import Protocol

from eleicoes_api.domain.schemas import (
    CandidateVotesByState,
    ElectionResults,
)


class ElectionRepository(Protocol):
    async def get_results(
        self,
        year: int,
        office: str,
        state: str | None = None,
        turn: int = 1,
    ) -> ElectionResults:
        """Retorna resultados eleitorais nacionais ou estaduais."""

    async def get_candidate_votes_by_state(
        self,
        year: int,
        office: str,
        candidate_name: str,
        turn: int = 1,
    ) -> CandidateVotesByState:
        """Retorna os dados do candidato, o total nacional e os votos por UF."""