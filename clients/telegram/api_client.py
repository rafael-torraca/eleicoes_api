from typing import Any

import httpx


class ElectionAPIError(Exception):
    """Erro ao consumir a Eleições API."""


class ElectionAPIClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
        )

    async def get_election_results(
        self,
        office: str = "presidente",
        year: int | None = None,
        state: str | None = None,
        turn: int = 1,
    ) -> dict[str, Any]:
        """Consulta os resultados nacionais ou de uma UF."""

        params: dict[str, str | int] = {
            "turno": turn,
        }

        if year is not None:
            params["ano"] = year

        if state:
            params["uf"] = state.upper()

        return await self._get(
            f"/v1/eleicoes/cargos/{office}/resultados",
            params=params,
        )

    async def get_candidate_votes_by_state(
        self,
        candidate: str,
        office: str = "presidente",
        year: int | None = None,
        turn: int = 1,
    ) -> dict[str, Any]:
        """Consulta o total nacional e os votos do candidato por UF."""

        params: dict[str, str | int] = {
            "candidato": candidate,
            "turno": turn,
        }

        if year is not None:
            params["ano"] = year

        return await self._get(
            f"/v1/eleicoes/cargos/{office}/votos-por-uf",
            params=params,
        )

    async def _get(
        self,
        path: str,
        params: dict[str, str | int],
    ) -> dict[str, Any]:
        """Executa uma requisição GET e valida sua resposta."""

        try:
            response = await self._client.get(
                path,
                params=params,
            )
            response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            try:
                error_data = exc.response.json()
            except ValueError:
                error_data = {}

            if isinstance(error_data, dict):
                message = (
                    error_data.get("message")
                    or error_data.get("detail")
                    or "A API não conseguiu processar a consulta."
                )
            else:
                message = "A API não conseguiu processar a consulta."

            raise ElectionAPIError(
                f"Erro HTTP {exc.response.status_code}: {message}"
            ) from exc

        except httpx.RequestError as exc:
            raise ElectionAPIError(
                "Não foi possível conectar à Eleições API. "
                "Verifique se a FastAPI está em execução."
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise ElectionAPIError(
                "A Eleições API retornou uma resposta inválida."
            ) from exc

        if not isinstance(data, dict):
            raise ElectionAPIError(
                "A Eleições API retornou um formato inesperado."
            )

        return data

    async def close(self) -> None:
        """Fecha o cliente HTTP e libera os recursos."""
        await self._client.aclose()