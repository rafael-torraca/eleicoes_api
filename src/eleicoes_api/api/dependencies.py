from typing import Annotated

from fastapi import Depends, Request

from eleicoes_api.application.election_service import ElectionService
from eleicoes_api.infrastructure.tse.repository import TSEElectionRepository


def get_election_service(request: Request) -> ElectionService:
    client = request.app.state.tse_client
    repository = TSEElectionRepository(client)

    return ElectionService(repository)


ElectionServiceDep = Annotated[
    ElectionService,
    Depends(get_election_service),
]