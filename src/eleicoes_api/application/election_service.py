from eleicoes_api.domain.repositories import ElectionRepository
from eleicoes_api.domain.schemas import (
    CandidateVotesByState,
    ElectionResults,
)


class ElectionService:
    def __init__(self, repository: ElectionRepository) -> None:
        self._repository = repository

    async def get_results(
        self,
        year: int,
        office: str,
        state: str | None = None,
        turn: int = 1,
    ) -> ElectionResults:
        office = office.strip().lower()
        state = state.strip().upper() if state and state.strip() else None

        self._validate_query(year, office, turn)

        return await self._repository.get_results(
            year=year,
            office=office,
            state=state,
            turn=turn,
        )

    async def get_candidate_votes_by_state(
        self,
        year: int,
        office: str,
        candidate_name: str,
        turn: int = 1,
    ) -> CandidateVotesByState:
        office = office.strip().lower()
        candidate_name = candidate_name.strip()

        self._validate_query(year, office, turn)

        if not candidate_name:
            raise ValueError(
                "O nome ou número do candidato é obrigatório."
            )

        return await self._repository.get_candidate_votes_by_state(
            year=year,
            office=office,
            candidate_name=candidate_name,
            turn=turn,
        )

    @staticmethod
    def _validate_query(
        year: int,
        office: str,
        turn: int,
    ) -> None:
        if not office:
            raise ValueError("O cargo eleitoral é obrigatório.")

        if year < 1900:
            raise ValueError("O ano da eleição é inválido.")

        if turn not in (1, 2):
            raise ValueError("O turno deve ser 1 ou 2.")

        if turn == 2 and office != "presidente":
            raise ValueError(
                "A consulta do segundo turno está disponível "
                "inicialmente apenas para presidente."
            )