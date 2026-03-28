import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.services.test_runner import run_project_tests

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    success: bool
    output: str
    errors: str
    workspace_path: str


class ValidatorAgent:
    def validate(self, code: str, filename: str, tests: str) -> ValidationResult:
        cleaned_code = code.strip()
        safe_filename = Path(filename).name.strip()
        cleaned_tests = tests.strip()
        if not cleaned_code:
            raise ValueError("Nenhum codigo foi enviado para validacao.")
        if not safe_filename:
            raise ValueError("O nome do arquivo eh obrigatorio para validacao.")
        if not cleaned_tests:
            raise ValueError("Nenhum teste foi enviado para validacao.")

        root = settings.allowed_execution_root.resolve()
        temp_root = root / ".qa_orchestrator_runs"
        temp_root.mkdir(parents=True, exist_ok=True)

        logger.info("Validator preparando workspace temporario para %s", safe_filename)
        with tempfile.TemporaryDirectory(dir=temp_root, prefix="qa_run_") as workspace:
            workspace_path = Path(workspace)
            source_file = workspace_path / safe_filename
            test_file = workspace_path / f"test_{Path(safe_filename).stem}.py"

            source_file.write_text(cleaned_code + "\n", encoding="utf-8")
            test_file.write_text(cleaned_tests + "\n", encoding="utf-8")

            result = run_project_tests(str(workspace_path))
            logger.info(
                "Validator concluiu execucao para %s com sucesso=%s",
                safe_filename,
                result["success"],
            )
            return ValidationResult(
                success=bool(result["success"]),
                output=str(result["output"]),
                errors=str(result["errors"]),
                workspace_path=str(workspace_path),
            )
