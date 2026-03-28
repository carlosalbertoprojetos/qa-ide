import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.agents import GeneratorAgent, PlannerAgent, ValidationResult, ValidatorAgent
from app.config import settings

logger = logging.getLogger(__name__)

MAX_VALIDATION_ATTEMPTS = 3


@dataclass
class AttemptOutcome:
    attempt: int
    success: bool
    output: str
    errors: str
    corrected: bool


@dataclass
class FullAuditResultPayload:
    success: bool
    auto_corrected: bool
    total_attempts: int
    attempts: list[AttemptOutcome]


@dataclass
class FullAuditOutcome:
    plan: str
    tests: str
    result: FullAuditResultPayload
    fixed_tests: str
    history_path: str
    created_at: str


class QAOrchestrator:
    def __init__(
        self,
        planner: PlannerAgent | None = None,
        generator: GeneratorAgent | None = None,
        validator: ValidatorAgent | None = None,
    ) -> None:
        self._planner = planner or PlannerAgent()
        self._generator = generator or GeneratorAgent()
        self._validator = validator or ValidatorAgent()

    def run_full_audit(self, code: str, filename: str) -> FullAuditOutcome:
        logger.info("Iniciando auditoria completa para %s", filename)
        plan = self._planner.create_test_plan(code, filename)
        initial_tests = self._generator.generate_tests(code=code, filename=filename, plan=plan)

        current_tests = initial_tests
        attempts: list[AttemptOutcome] = []
        final_validation: ValidationResult | None = None

        for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
            logger.info("Executando tentativa %s de validacao para %s", attempt, filename)
            validation = self._validator.validate(code=code, filename=filename, tests=current_tests)
            final_validation = validation
            corrected = attempt > 1
            attempts.append(
                AttemptOutcome(
                    attempt=attempt,
                    success=validation.success,
                    output=validation.output.strip(),
                    errors=validation.errors.strip(),
                    corrected=corrected,
                )
            )

            if validation.success:
                logger.info("Auditoria completa concluida com sucesso na tentativa %s", attempt)
                break

            if attempt < MAX_VALIDATION_ATTEMPTS:
                logger.warning("Validator encontrou falhas na tentativa %s; acionando generator para correcao", attempt)
                current_tests = self._generator.generate_tests(
                    code=code,
                    filename=filename,
                    plan=plan,
                    validation_feedback=validation.errors or validation.output,
                    previous_tests=current_tests,
                )

        if final_validation is None:
            raise RuntimeError("Falha interna: nenhuma validacao foi executada.")

        result = FullAuditResultPayload(
            success=final_validation.success,
            auto_corrected=current_tests != initial_tests,
            total_attempts=len(attempts),
            attempts=attempts,
        )
        created_at = datetime.now(timezone.utc).isoformat()
        history_path = self._persist_history(
            code=code,
            filename=filename,
            created_at=created_at,
            plan=plan,
            tests=initial_tests,
            result=result,
            fixed_tests=current_tests,
        )

        return FullAuditOutcome(
            plan=plan,
            tests=initial_tests,
            result=result,
            fixed_tests=current_tests,
            history_path=history_path,
            created_at=created_at,
        )

    def _persist_history(
        self,
        *,
        code: str,
        filename: str,
        created_at: str,
        plan: str,
        tests: str,
        result: FullAuditResultPayload,
        fixed_tests: str,
    ) -> str:
        history_root = settings.allowed_execution_root.resolve() / ".qa_audit_history"
        history_root.mkdir(parents=True, exist_ok=True)
        self._cleanup_history(history_root)

        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(filename).stem).strip("._") or "audit"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        history_file = history_root / f"{timestamp}_{safe_name}.json"

        payload = {
            "created_at": created_at,
            "filename": filename,
            "source_sha256": hashlib.sha256(code.encode("utf-8")).hexdigest(),
            "plan": plan,
            "tests": tests,
            "result": {
                "success": result.success,
                "auto_corrected": result.auto_corrected,
                "total_attempts": result.total_attempts,
                "attempts": [
                    {
                        "attempt": attempt.attempt,
                        "success": attempt.success,
                        "output": attempt.output,
                        "errors": attempt.errors,
                        "corrected": attempt.corrected,
                    }
                    for attempt in result.attempts
                ],
            },
            "fixed_tests": fixed_tests,
        }
        history_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Historico estruturado salvo em %s", history_file)
        return str(history_file)

    def _cleanup_history(self, history_root: Path) -> None:
        history_files = sorted(history_root.glob("*.json"), key=lambda item: item.stat().st_mtime)
        if not history_files:
            return

        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_history_max_age_days)
        for history_file in list(history_files):
            modified_at = datetime.fromtimestamp(history_file.stat().st_mtime, tz=timezone.utc)
            if modified_at < cutoff:
                logger.info("Removendo historico expirado: %s", history_file)
                history_file.unlink(missing_ok=True)

        remaining_files = sorted(history_root.glob("*.json"), key=lambda item: item.stat().st_mtime)
        overflow = len(remaining_files) - settings.audit_history_max_files
        if overflow <= 0:
            return

        for history_file in remaining_files[:overflow]:
            logger.info("Removendo historico excedente: %s", history_file)
            history_file.unlink(missing_ok=True)


def run_full_audit(code: str, filename: str) -> dict[str, object]:
    outcome = QAOrchestrator().run_full_audit(code=code, filename=filename)
    return {
        "plan": outcome.plan,
        "tests": outcome.tests,
        "result": {
            "success": outcome.result.success,
            "auto_corrected": outcome.result.auto_corrected,
            "total_attempts": outcome.result.total_attempts,
            "attempts": [
                {
                    "attempt": attempt.attempt,
                    "success": attempt.success,
                    "output": attempt.output,
                    "errors": attempt.errors,
                    "corrected": attempt.corrected,
                }
                for attempt in outcome.result.attempts
            ],
        },
        "fixed_tests": outcome.fixed_tests,
        "history_path": outcome.history_path,
        "created_at": outcome.created_at,
    }
