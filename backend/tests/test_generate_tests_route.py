from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_generate_tests_returns_generated_code(monkeypatch):
    def fake_generate_tests(code: str, filename: str) -> str:
        assert code == "def add(a, b):\n    return a + b\n"
        assert filename == "math_utils.py"
        return "import pytest\n\n\ndef test_add():\n    assert True\n"

    monkeypatch.setattr("app.routes.test_generation.generate_tests", fake_generate_tests)

    response = client.post(
        "/generate-tests",
        json={"code": "def add(a, b):\n    return a + b\n", "filename": "math_utils.py"},
    )

    assert response.status_code == 200
    assert response.json() == {"tests": "import pytest\n\n\ndef test_add():\n    assert True\n"}


def test_generate_tests_returns_bad_request_for_invalid_payload(monkeypatch):
    def fake_generate_tests(code: str, filename: str) -> str:
        raise ValueError("Nenhum codigo foi enviado para gerar testes.")

    monkeypatch.setattr("app.routes.test_generation.generate_tests", fake_generate_tests)

    response = client.post("/generate-tests", json={"code": "   ", "filename": "empty.py"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Nenhum codigo foi enviado para gerar testes."}


def test_run_tests_returns_structured_result(monkeypatch):
    def fake_run_project_tests(project_path: str) -> dict[str, object]:
        assert project_path == "workspace-test"
        return {
            "success": True,
            "output": "[pytest]\nstatus: passou",
            "errors": "",
        }

    monkeypatch.setattr("app.routes.test_execution.run_project_tests", fake_run_project_tests)

    response = client.post("/run-tests", json={"path": "workspace-test"})

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "output": "[pytest]\nstatus: passou",
        "errors": "",
    }


def test_run_tests_returns_bad_request_for_invalid_path(monkeypatch):
    def fake_run_project_tests(project_path: str) -> dict[str, object]:
        raise ValueError("Execucao fora do diretorio permitido: C:\\forbidden")

    monkeypatch.setattr("app.routes.test_execution.run_project_tests", fake_run_project_tests)

    response = client.post("/run-tests", json={"path": "C:\\forbidden"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Execucao fora do diretorio permitido: C:\\forbidden"}


def test_full_audit_route_returns_structured_payload(monkeypatch):
    def fake_run_full_audit(code: str, filename: str) -> dict[str, object]:
        assert code == "def add(a, b):\n    return a + b\n"
        assert filename == "math_utils.py"
        return {
            "plan": "Plano gerado",
            "tests": "import pytest",
            "result": {
                "success": True,
                "auto_corrected": False,
                "total_attempts": 1,
                "attempts": [
                    {
                        "attempt": 1,
                        "success": True,
                        "output": "1 passed in 0.01s",
                        "errors": "",
                        "corrected": False,
                    }
                ],
            },
            "fixed_tests": "import pytest",
            "history_path": "C:\\qa\\.qa_audit_history\\20260328T120000Z_math_utils.json",
            "created_at": "2026-03-28T12:00:00+00:00",
        }

    monkeypatch.setattr("app.routes.full_audit.run_full_audit", fake_run_full_audit)

    response = client.post(
        "/full-audit",
        json={"code": "def add(a, b):\n    return a + b\n", "filename": "math_utils.py"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "plan": "Plano gerado",
        "tests": "import pytest",
        "result": {
            "success": True,
            "auto_corrected": False,
            "total_attempts": 1,
            "attempts": [
                {
                    "attempt": 1,
                    "success": True,
                    "output": "1 passed in 0.01s",
                    "errors": "",
                    "corrected": False,
                }
            ],
        },
        "fixed_tests": "import pytest",
        "history_path": "C:\\qa\\.qa_audit_history\\20260328T120000Z_math_utils.json",
        "created_at": "2026-03-28T12:00:00+00:00",
    }
