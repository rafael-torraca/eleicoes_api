from fastapi.testclient import TestClient

from eleicoes_api.main import create_app


def test_unknown_route_returns_standardized_404() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/rota-inexistente")

    assert response.status_code == 404
    assert response.json() == {
        "error": "not_found",
        "message": "Not Found",
    }


def test_method_not_allowed_returns_standardized_response() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.post("/health")

    assert response.status_code == 405
    assert response.json() == {
        "error": "method_not_allowed",
        "message": "Method Not Allowed",
    }