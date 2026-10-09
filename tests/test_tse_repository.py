import pytest

from eleicoes_api.domain.errors import (
    ElectionDataUnavailableError,
    ElectionResourceNotFoundError,
)
from eleicoes_api.infrastructure.tse.repository import (
    TSEElectionRepository,
)


def build_results_payload(
    candidates: list[tuple[int, str, str, int]],
) -> dict:
    """Cria um JSON fictício no formato esperado pelo parser."""
    parties = []

    for number, name, party, votes in candidates:
        parties.append(
            {
                "sg": party,
                "cand": [
                    {
                        "nm": name,
                        "n": str(number),
                        "vap": str(votes),
                    }
                ],
            }
        )

    return {
        "carg": [
            {
                "cd": "1",
                "agr": [
                    {
                        "par": parties,
                    }
                ],
            }
        ]
    }


ELECTION_CONFIG = {
    "pl": [
        {
            "c": "ele2026",
            "e": [
                {
                    "t": "1",
                    "cd": "6257",
                    "cdt2": "6260",
                    "abr": [
                        {
                            "cp": [{"cd": "1"}],
                        }
                    ],
                }
            ],
        }
    ]
}


class FakeTSEClient:
    """Simula o cliente do TSE sem acessar a internet."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def get_json(self, url: str) -> dict:
        return self.payload


class FakeCandidateVotesClient:
    """Simula resultados nacionais e estaduais."""

    async def get_json(self, url: str) -> dict:
        if "ele-c.json" in url:
            return ELECTION_CONFIG

        if "/dados/br/" in url:
            return build_results_payload(
                [
                    (22, "CANDIDATO TESTE", "PL", 4000),
                    (13, "OUTRO CANDIDATO", "PT", 3000),
                ]
            )

        if "/dados/mg/" in url:
            return build_results_payload(
                [
                    (22, "CANDIDATO TESTE", "PL", 1500),
                    (13, "OUTRO CANDIDATO", "PT", 100),
                ]
            )

        if "/dados/sp/" in url:
            return build_results_payload(
                [
                    (22, "CANDIDATO TESTE", "PL", 2500),
                    (13, "OUTRO CANDIDATO", "PT", 200),
                ]
            )

        return build_results_payload(
            [
                (13, "OUTRO CANDIDATO", "PT", 50),
            ]
        )


def test_parse_candidates_orders_by_votes() -> None:
    repository = TSEElectionRepository(
        client=FakeTSEClient({})
    )

    payload = build_results_payload(
        [
            (22, "CANDIDATO A", "PL", 150),
            (13, "CANDIDATO B", "PT", 300),
        ]
    )

    candidates = repository._parse_candidates(
        payload,
        office_code="0001",
    )

    assert len(candidates) == 2
    assert candidates[0].name == "CANDIDATO B"
    assert candidates[0].votes == 300
    assert candidates[1].name == "CANDIDATO A"
    assert candidates[1].votes == 150


@pytest.mark.asyncio
async def test_resolves_second_turn_from_config() -> None:
    repository = TSEElectionRepository(
        client=FakeTSEClient(ELECTION_CONFIG)
    )

    cycle, election_code = await repository._resolve_election_code(
        year=2026,
        office="presidente",
        turn=2,
    )

    assert cycle == "ele2026"
    assert election_code == "6260"


@pytest.mark.asyncio
async def test_second_turn_missing_results_returns_clear_error() -> None:
    class MissingSecondTurnClient:
        async def get_json(self, url: str) -> dict:
            if "ele-c.json" in url:
                return ELECTION_CONFIG

            raise ElectionResourceNotFoundError(
                "Recurso não encontrado no TSE."
            )

    repository = TSEElectionRepository(
        client=MissingSecondTurnClient()
    )

    with pytest.raises(
        ElectionDataUnavailableError,
        match="arquivo de resultados do segundo turno presidencial",
    ):
        await repository.get_results(
            year=2026,
            office="presidente",
            state="MG",
            turn=2,
        )


@pytest.mark.asyncio
async def test_candidate_votes_returns_national_total_and_states() -> None:
    repository = TSEElectionRepository(
        client=FakeCandidateVotesClient()
    )

    result = await repository.get_candidate_votes_by_state(
        year=2026,
        office="presidente",
        candidate_name="22",
        turn=1,
    )

    assert result.year == 2026
    assert result.office == "presidente"
    assert result.turn == 1

    assert result.candidate_number == 22
    assert result.candidate_name == "CANDIDATO TESTE"
    assert result.party == "PL"

    assert result.total_votes == 4000
    assert result.votes_by_state["MG"] == 1500
    assert result.votes_by_state["SP"] == 2500

    assert len(result.votes_by_state) == 27
    assert result.votes_by_state["AC"] == 0


@pytest.mark.asyncio
async def test_election_config_uses_cache() -> None:
    class CountingConfigClient:
        def __init__(self) -> None:
            self.config_requests = 0

        async def get_json(self, url: str) -> dict:
            if "ele-c.json" in url:
                self.config_requests += 1
                return ELECTION_CONFIG

            raise AssertionError(
                f"URL inesperada neste teste: {url}"
            )

    client = CountingConfigClient()
    repository = TSEElectionRepository(client=client)

    first_result = await repository._resolve_election_code(
        year=2026,
        office="presidente",
        turn=1,
    )

    second_result = await repository._resolve_election_code(
        year=2026,
        office="presidente",
        turn=2,
    )

    assert first_result == ("ele2026", "6257")
    assert second_result == ("ele2026", "6260")

    # A configuração deve ser solicitada apenas uma vez.
    assert client.config_requests == 1