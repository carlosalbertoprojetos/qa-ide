import json
import os
from pathlib import Path

from app.config import settings
from app.services.qa_orchestrator import FullAuditOutcome, QAOrchestrator
from app.services.test_generator import _extract_python_code
from app.services.test_runner import _detect_playwright_project, run_project_tests


def test_extract_python_code_from_markdown_fence():
    content = "```python\nimport pytest\n\ndef test_ok():\n    assert True\n```"

    assert _extract_python_code(content) == "import pytest\n\ndef test_ok():\n    assert True"


def test_extract_python_code_without_markdown_fence():
    content = "import pytest\n\ndef test_ok():\n    assert True\n"

    assert _extract_python_code(content) == "import pytest\n\ndef test_ok():\n    assert True"


def test_run_project_tests_executes_pytest_in_allowed_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "allowed_execution_root", tmp_path)

    project_dir = tmp_path / "sample_project"
    project_dir.mkdir()
    (project_dir / "test_sample.py").write_text(
        "def test_ok():\n    assert 1 + 1 == 2\n",
        encoding="utf-8",
    )

    result = run_project_tests(str(project_dir))

    assert result["success"] is True
    assert "[pytest]" in result["output"]
    assert "1 passed" in result["output"]
    assert result["errors"] == ""


def test_run_project_tests_rejects_path_outside_allowed_root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "allowed_execution_root", tmp_path)

    outside_dir = tmp_path.parent / "outside_project"
    outside_dir.mkdir(exist_ok=True)

    try:
        run_project_tests(str(outside_dir))
    except ValueError as exc:
        assert "Execucao fora do diretorio permitido" in str(exc)
    else:
        raise AssertionError("Era esperado bloquear execucao fora do diretorio permitido.")


def test_detect_playwright_project_finds_frontend_with_local_binary(tmp_path):
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / "package.json").write_text(
        '{"dependencies": {"react": "18.0.0"}, "devDependencies": {"@playwright/test": "1.0.0"}}',
        encoding="utf-8",
    )
    (frontend_dir / "playwright.config.ts").write_text("export default {};\n", encoding="utf-8")
    bin_dir = frontend_dir / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    playwright_bin = bin_dir / ("playwright.cmd" if os.name == "nt" else "playwright")
    playwright_bin.write_text("", encoding="utf-8")

    frontend_detected, playwright_project = _detect_playwright_project(tmp_path)

    assert frontend_detected is True
    assert playwright_project == frontend_dir


def test_full_audit_orchestrator_retries_failed_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "allowed_execution_root", tmp_path)

    class FakePlanner:
        def create_test_plan(self, code: str, filename: str) -> str:
            assert filename == "service.py"
            return "Plano de testes"

    class FakeGenerator:
        def __init__(self) -> None:
            self.calls = 0

        def generate_tests(
            self,
            *,
            code: str,
            filename: str,
            plan: str | None = None,
            validation_feedback: str | None = None,
            previous_tests: str | None = None,
        ) -> str:
            self.calls += 1
            if self.calls == 1:
                assert validation_feedback is None
                return "import pytest\n\ndef test_initial():\n    assert False\n"

            assert validation_feedback == "AssertionError: boom"
            assert previous_tests is not None
            return "import pytest\n\ndef test_fixed():\n    assert True\n"

    class FakeValidator:
        def __init__(self) -> None:
            self.calls = 0

        def validate(self, code: str, filename: str, tests: str):
            self.calls += 1
            if self.calls == 1:
                return type(
                    "Validation",
                    (),
                    {
                        "success": False,
                        "output": "FAILED test_initial",
                        "errors": "AssertionError: boom",
                        "workspace_path": str(tmp_path / "qa1"),
                    },
                )()

            return type(
                "Validation",
                (),
                {
                    "success": True,
                    "output": "1 passed in 0.01s",
                    "errors": "",
                    "workspace_path": str(tmp_path / "qa2"),
                },
            )()

    orchestrator = QAOrchestrator(
        planner=FakePlanner(),
        generator=FakeGenerator(),
        validator=FakeValidator(),
    )

    result = orchestrator.run_full_audit("def service():\n    return True\n", "service.py")

    assert isinstance(result, FullAuditOutcome)
    assert result.plan == "Plano de testes"
    assert "test_initial" in result.tests
    assert "test_fixed" in result.fixed_tests
    assert result.result.success is True
    assert result.result.auto_corrected is True
    assert result.result.total_attempts == 2
    assert result.result.attempts[0].attempt == 1
    assert result.result.attempts[0].success is False
    assert result.result.attempts[0].corrected is False
    assert result.result.attempts[1].attempt == 2
    assert result.result.attempts[1].success is True
    assert result.result.attempts[1].corrected is True
    history_file = Path(result.history_path)
    assert history_file.exists()
    history_payload = json.loads(history_file.read_text(encoding="utf-8"))
    assert history_payload["filename"] == "service.py"
    assert history_payload["result"]["total_attempts"] == 2
    assert history_payload["result"]["attempts"][1]["corrected"] is True
    assert result.created_at.endswith("+00:00")


def test_full_audit_history_cleanup_removes_old_and_excess_files(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "allowed_execution_root", tmp_path)
    monkeypatch.setattr(settings, "audit_history_max_files", 2)
    monkeypatch.setattr(settings, "audit_history_max_age_days", 1)

    history_dir = tmp_path / ".qa_audit_history"
    history_dir.mkdir()

    expired_file = history_dir / "expired.json"
    expired_file.write_text("{}", encoding="utf-8")
    old_timestamp = expired_file.stat().st_mtime - (3 * 24 * 60 * 60)
    os.utime(expired_file, (old_timestamp, old_timestamp))

    keep_one = history_dir / "keep_one.json"
    keep_one.write_text("{}", encoding="utf-8")
    keep_two = history_dir / "keep_two.json"
    keep_two.write_text("{}", encoding="utf-8")

    orchestrator = QAOrchestrator()
    orchestrator._cleanup_history(history_dir)

    remaining = sorted(item.name for item in history_dir.glob("*.json"))
    assert "expired.json" not in remaining
    assert len(remaining) == 2
