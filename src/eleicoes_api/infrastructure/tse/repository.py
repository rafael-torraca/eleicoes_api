import asyncio
import unicodedata

from eleicoes_api.domain.errors import (
    CandidateNotFoundError,
    ElectionDataUnavailableError,
    ElectionResourceNotFoundError,
)
from eleicoes_api.domain.repositories import ElectionRepository
from eleicoes_api.domain.schemas import (
    CandidateResult,
    CandidateVotesByState,
    ElectionResults,
)
from eleicoes_api.infrastructure.tse.client import TSEClient


class TSEElectionRepository(ElectionRepository):
    BASE_URL = "https://resultados.tse.jus.br"
    MAX_CONCURRENT_STATE_REQUESTS = 4

    STATES = (
        "AC", "AL", "AP", "AM", "BA", "CE", "DF",
        "ES", "GO", "MA", "MT", "MS", "MG", "PA",
        "PB", "PR", "PE", "PI", "RJ", "RN", "RS",
        "RO", "RR", "SC", "SP", "SE", "TO",
    )

    OFFICE_CODES = {
        "presidente": "0001",
        "governador": "0003",
        "senador": "0005",
        "deputado federal": "0006",
        "deputado estadual": "0007",
        "deputado distrital": "0008",
    }

    def __init__(self, client: TSEClient) -> None:
        self._client = client
        self._election_config_cache: dict[int, dict] = {}

    async def get_results(
        self,
        year: int,
        office: str,
        state: str | None = None,
        turn: int = 1,
    ) -> ElectionResults:
        office = self._normalize_office(office)
        self._validate_query(year, office, turn)

        if state and state.strip():
            state = state.strip().upper()

            if state not in self.STATES:
                raise ValueError(f"UF inválida: {state}")
        else:
            state = None

        cycle, election_code = await self._resolve_election_code(
            year=year,
            office=office,
            turn=turn,
        )

        url = self._build_url(
            cycle=cycle,
            election_code=election_code,
            office=office,
            state=state,
        )

        try:
            payload = await self._client.get_json(url)

        except ElectionResourceNotFoundError as exc:
            if office == "presidente" and turn == 2:
                raise ElectionDataUnavailableError(
                    "O arquivo de resultados do segundo turno "
                    "presidencial não foi encontrado no TSE. Os "
                    "resultados podem ainda não ter sido publicados "
                    "ou o endereço oficial pode ter mudado."
                ) from exc

            raise

        if not isinstance(payload, dict):
            raise ElectionDataUnavailableError(
                "O TSE retornou um formato de dados inesperado."
            )

        candidates = self._parse_candidates(
            payload,
            self.OFFICE_CODES[office],
        )

        return ElectionResults(
            year=year,
            office=office,
            state=state,
            candidates=candidates,
        )

    async def get_candidate_votes_by_state(
        self,
        year: int,
        office: str,
        candidate_name: str,
        turn: int = 1,
    ) -> CandidateVotesByState:
        office = self._normalize_office(office)
        candidate_name = candidate_name.strip()

        if office != "presidente":
            raise ValueError(
                "A consulta de votos por estado está disponível "
                "inicialmente apenas para presidente."
            )

        if not candidate_name:
            raise ValueError(
                "Informe o nome ou número do candidato."
            )

        # Consulta o resultado nacional para identificar o candidato
        # e obter seu total oficial de votos.
        national_results = await self.get_results(
            year=year,
            office=office,
            turn=turn,
        )

        candidate = self._find_candidate(
            national_results.candidates,
            candidate_name,
        )

        # Limita quantas consultas estaduais acontecem ao mesmo tempo.
        semaphore = asyncio.Semaphore(
            self.MAX_CONCURRENT_STATE_REQUESTS
        )

        async def fetch_state_votes(
            state: str,
        ) -> tuple[str, int]:
            async with semaphore:
                results = await self.get_results(
                    year=year,
                    office=office,
                    state=state,
                    turn=turn,
                )

            state_candidate = next(
                (
                    item
                    for item in results.candidates
                    if item.number == candidate.number
                ),
                None,
            )

            votes = (
                state_candidate.votes
                if state_candidate is not None
                else 0
            )

            return state, votes

        # As tarefas são executadas em paralelo, respeitando o limite.
        state_results = await asyncio.gather(
            *(
                fetch_state_votes(state)
                for state in self.STATES
            )
        )

        votes_by_state = dict(state_results)

        return CandidateVotesByState(
            year=year,
            office=office,
            turn=turn,
            candidate_number=candidate.number,
            candidate_name=candidate.name,
            party=candidate.party,
            total_votes=candidate.votes,
            votes_by_state=votes_by_state,
        )

    async def _get_election_config(self, year: int) -> dict:
        if year in self._election_config_cache:
            return self._election_config_cache[year]

        config_url = (
            f"{self.BASE_URL}/oficial/"
            "comum/config/ele-c.json"
        )

        payload = await self._client.get_json(config_url)

        if not isinstance(payload, dict):
            raise ElectionDataUnavailableError(
                "A configuração de eleições do TSE é inválida."
            )

        if not isinstance(payload.get("pl"), list):
            raise ElectionDataUnavailableError(
                "A configuração do TSE não contém a lista de pleitos."
            )

        self._election_config_cache[year] = payload

        return payload

    async def _resolve_election_code(
        self,
        year: int,
        office: str,
        turn: int,
    ) -> tuple[str, str]:
        config = await self._get_election_config(year)
        office_code = self.OFFICE_CODES[office]

        direct_matches: list[tuple[str, str]] = []
        second_turn_matches: list[tuple[str, str]] = []

        for pleito in config["pl"]:
            cycle = str(pleito.get("c", "")).strip()

            if not cycle:
                continue

            for election in pleito.get("e", []):
                if not self._election_has_office(
                    election,
                    office_code,
                ):
                    continue

                election_turn = str(election.get("t", "1"))
                election_code = election.get("cd")

                if (
                    election_turn == str(turn)
                    and election_code is not None
                ):
                    direct_matches.append(
                        (cycle, str(election_code))
                    )

                second_turn_code = election.get("cdt2")

                if (
                    election_turn == "1"
                    and second_turn_code is not None
                ):
                    second_turn_matches.append(
                        (cycle, str(second_turn_code))
                    )

        if direct_matches:
            return self._select_unique_match(
                direct_matches,
                turn,
            )

        if turn == 2 and second_turn_matches:
            return self._select_unique_match(
                second_turn_matches,
                turn,
            )

        raise ElectionDataUnavailableError(
            f"O código da eleição para {office}, turno {turn}, "
            f"não foi encontrado na configuração do TSE para {year}."
        )

    @staticmethod
    def _select_unique_match(
        matches: list[tuple[str, str]],
        turn: int,
    ) -> tuple[str, str]:
        unique_matches = list(dict.fromkeys(matches))

        if len(unique_matches) != 1:
            raise ElectionDataUnavailableError(
                f"A configuração do TSE apresenta códigos "
                f"ambíguos para o turno {turn}."
            )

        return unique_matches[0]

    @staticmethod
    def _election_has_office(
        election: dict,
        office_code: str,
    ) -> bool:
        for coverage in election.get("abr", []):
            for office_data in coverage.get("cp", []):
                code = str(office_data.get("cd", "")).zfill(4)

                if code == office_code:
                    return True

        return False

    def _build_url(
        self,
        cycle: str,
        election_code: str,
        office: str,
        state: str | None,
    ) -> str:
        scope = state.lower() if state else "br"
        office_code = self.OFFICE_CODES[office]
        formatted_election_code = election_code.zfill(6)

        filename = (
            f"{scope}-c{office_code}-"
            f"e{formatted_election_code}-u.json"
        )

        return (
            f"{self.BASE_URL}/oficial/{cycle}/"
            f"{election_code}/dados/{scope}/{filename}"
        )

    def _parse_candidates(
        self,
        payload: dict,
        office_code: str,
    ) -> list[CandidateResult]:
        candidates = []

        for office_data in payload.get("carg", []):
            code = str(office_data.get("cd", "")).zfill(4)

            if code != office_code:
                continue

            for aggregation in office_data.get("agr", []):
                for party in aggregation.get("par", []):
                    for candidate in party.get("cand", []):
                        name = candidate.get("nm")
                        number = candidate.get("n")

                        if name is None or number is None:
                            continue

                        candidates.append(
                            CandidateResult(
                                number=int(number),
                                name=name,
                                party=party.get("sg"),
                                votes=int(candidate.get("vap", 0)),
                            )
                        )

        if not candidates:
            raise ElectionDataUnavailableError(
                "Não foram encontrados candidatos no arquivo do TSE."
            )

        return sorted(
            candidates,
            key=lambda candidate: candidate.votes,
            reverse=True,
        )

    def _find_candidate(
        self,
        candidates: list[CandidateResult],
        query: str,
    ) -> CandidateResult:
        query = query.strip()

        if not query:
            raise ValueError(
                "Informe o nome ou número do candidato."
            )

        if query.isdigit():
            matches = [
                candidate
                for candidate in candidates
                if candidate.number == int(query)
            ]
        else:
            query_terms = self._normalize_name(query).split()

            matches = [
                candidate
                for candidate in candidates
                if all(
                    term in self._normalize_name(candidate.name).split()
                    for term in query_terms
                )
            ]

        if not matches:
            raise CandidateNotFoundError(
                f"Candidato não encontrado: {query}"
            )

        if len(matches) > 1:
            raise ElectionDataUnavailableError(
                "Mais de um candidato corresponde à busca. "
                "Informe um nome mais específico ou o número."
            )

        return matches[0]

    @staticmethod
    def _validate_query(
        year: int,
        office: str,
        turn: int,
    ) -> None:
        if year != 2026:
            raise ElectionDataUnavailableError(
                "O repositório está configurado inicialmente para 2026."
            )

        if office not in TSEElectionRepository.OFFICE_CODES:
            raise ValueError(f"Cargo não suportado: {office}")

        if turn not in (1, 2):
            raise ValueError("O turno deve ser 1 ou 2.")

        if turn == 2 and office != "presidente":
            raise ValueError(
                "O segundo turno está implementado inicialmente "
                "apenas para presidente."
            )

    @staticmethod
    def _normalize_office(office: str) -> str:
        return " ".join(office.strip().lower().split())

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = unicodedata.normalize("NFKD", name)

        return "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        ).casefold()