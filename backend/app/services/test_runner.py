import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.config import settings

COMMAND_TIMEOUT_SECONDS = 120
IGNORED_SCAN_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    ".next",
    "coverage",
    "__pycache__",
}
PLAYWRIGHT_CONFIG_NAMES = (
    "playwright.config.ts",
    "playwright.config.js",
    "playwright.config.mjs",
    "playwright.config.cjs",
)
FRONTEND_DEPENDENCY_MARKERS = {
    "react",
    "next",
    "vue",
    "nuxt",
    "@angular/core",
    "svelte",
    "@sveltejs/kit",
    "vite",
    "solid-js",
}
PLAYWRIGHT_DEPENDENCY_MARKERS = {"@playwright/test", "playwright"}


@dataclass
class CommandResult:
    name: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


def run_project_tests(project_path: str) -> dict[str, object]:
    target_path = _resolve_project_path(project_path)
    pytest_result = _run_pytest(target_path)

    playwright_result: CommandResult | None = None
    frontend_detected, playwright_project = _detect_playwright_project(target_path)
    playwright_missing_reason = ""

    if playwright_project:
        playwright_result = _run_playwright(playwright_project)
    elif frontend_detected:
        playwright_missing_reason = (
            f"Frontend detectado em {target_path}, mas nenhuma configuracao valida do Playwright foi encontrada."
        )

    success = pytest_result.success
    if frontend_detected:
        success = success and playwright_result is not None and playwright_result.success

    output = _build_output(target_path, pytest_result, playwright_result, playwright_missing_reason)
    errors = _build_error_summary(pytest_result, playwright_result, playwright_missing_reason)

    return {
        "success": success,
        "output": output,
        "errors": errors,
    }


def _resolve_project_path(project_path: str) -> Path:
    if not project_path or not project_path.strip():
        raise ValueError("O caminho do projeto eh obrigatorio.")
    if "\x00" in project_path:
        raise ValueError("O caminho do projeto contem caracteres invalidos.")

    allowed_root = settings.allowed_execution_root.resolve()
    candidate = Path(project_path.strip()).expanduser()
    candidate = (allowed_root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()

    if not candidate.exists():
        raise ValueError(f"O caminho informado nao existe: {candidate}")
    if not candidate.is_dir():
        raise ValueError(f"O caminho informado nao eh um diretorio: {candidate}")
    if not _is_relative_to(candidate, allowed_root):
        raise ValueError(f"Execucao fora do diretorio permitido: {candidate}")

    return candidate


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _run_pytest(project_path: Path) -> CommandResult:
    return _run_command("pytest", [sys.executable, "-m", "pytest", "-q"], project_path)


def _run_playwright(project_path: Path) -> CommandResult:
    return _run_command("playwright", [_get_playwright_binary(project_path), "test"], project_path)


def _run_command(name: str, command: list[str], cwd: Path) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            shell=False,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Comando nao encontrado para {name}: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "").strip()
        stderr = (exc.stderr or "").strip()
        timeout_message = f"Tempo limite excedido apos {COMMAND_TIMEOUT_SECONDS}s."
        stderr = f"{stderr}\n{timeout_message}".strip()
        return CommandResult(name=name, command=command, returncode=1, stdout=stdout, stderr=stderr)

    return CommandResult(
        name=name,
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def _detect_playwright_project(project_path: Path) -> tuple[bool, Path | None]:
    frontend_detected = False

    for candidate in _iter_candidate_directories(project_path):
        has_frontend = _is_frontend_project(candidate)
        has_playwright_config = _has_playwright_config(candidate)
        has_playwright_dependency = _package_has_playwright_dependency(candidate)

        if has_frontend:
            frontend_detected = True

        if (has_frontend or has_playwright_config or has_playwright_dependency) and _has_playwright_binary(candidate):
            if has_playwright_config or has_playwright_dependency:
                return True, candidate

    return frontend_detected, None


def _iter_candidate_directories(project_path: Path) -> list[Path]:
    candidates = [project_path]
    for child in sorted(project_path.iterdir()):
        if child.is_dir() and child.name not in IGNORED_SCAN_DIRS:
            candidates.append(child)
    return candidates


def _is_frontend_project(project_path: Path) -> bool:
    package_json = project_path / "package.json"
    if not package_json.is_file():
        return False

    package_data = _load_package_json(package_json)
    dependency_names = {
        *package_data.get("dependencies", {}).keys(),
        *package_data.get("devDependencies", {}).keys(),
    }
    if dependency_names & FRONTEND_DEPENDENCY_MARKERS:
        return True

    return any(
        (project_path / marker).exists()
        for marker in ("src", "public", "app", "vite.config.ts", "vite.config.js", "next.config.js")
    )


def _package_has_playwright_dependency(project_path: Path) -> bool:
    package_json = project_path / "package.json"
    if not package_json.is_file():
        return False

    package_data = _load_package_json(package_json)
    dependency_names = {
        *package_data.get("dependencies", {}).keys(),
        *package_data.get("devDependencies", {}).keys(),
    }
    return bool(dependency_names & PLAYWRIGHT_DEPENDENCY_MARKERS)


def _load_package_json(package_json: Path) -> dict:
    try:
        return json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _has_playwright_config(project_path: Path) -> bool:
    return any((project_path / config_name).is_file() for config_name in PLAYWRIGHT_CONFIG_NAMES)


def _has_playwright_binary(project_path: Path) -> bool:
    return Path(_get_playwright_binary(project_path)).is_file()


def _get_playwright_binary(project_path: Path) -> str:
    binary_name = "playwright.cmd" if os.name == "nt" else "playwright"
    return str(project_path / "node_modules" / ".bin" / binary_name)


def _build_output(
    target_path: Path,
    pytest_result: CommandResult,
    playwright_result: CommandResult | None,
    playwright_missing_reason: str,
) -> str:
    sections = [
        "Projeto analisado:",
        str(target_path),
        "",
        _format_command_output(pytest_result),
    ]

    if playwright_result is not None:
        sections.extend(["", _format_command_output(playwright_result)])
    elif playwright_missing_reason:
        sections.extend(["", "[playwright]", "status: nao executado", playwright_missing_reason])

    return "\n".join(sections).strip()


def _format_command_output(result: CommandResult) -> str:
    parts = [
        f"[{result.name}]",
        f"status: {'passou' if result.success else 'falhou'}",
        f"comando: {' '.join(result.command)}",
    ]
    if result.stdout:
        parts.extend(["stdout:", result.stdout])
    if result.stderr:
        parts.extend(["stderr:", result.stderr])
    return "\n".join(parts)


def _build_error_summary(
    pytest_result: CommandResult,
    playwright_result: CommandResult | None,
    playwright_missing_reason: str,
) -> str:
    sections: list[str] = []

    pytest_errors = _extract_key_error_lines(pytest_result)
    if pytest_errors:
        sections.append("[pytest]\n" + pytest_errors)

    if playwright_result is not None:
        playwright_errors = _extract_key_error_lines(playwright_result)
        if playwright_errors:
            sections.append("[playwright]\n" + playwright_errors)
    elif playwright_missing_reason:
        sections.append("[playwright]\n" + playwright_missing_reason)

    return "\n\n".join(sections).strip()


def _extract_key_error_lines(result: CommandResult) -> str:
    if result.success and not result.stderr:
        return ""

    combined = "\n".join(part for part in (result.stdout, result.stderr) if part).splitlines()
    keywords = ("FAILED", "ERROR", "Traceback", "E   ", "AssertionError", "Timeout")
    relevant = [line.strip() for line in combined if line.strip() and any(keyword in line for keyword in keywords)]

    if not relevant:
        relevant = [line.strip() for line in combined if line.strip()][-12:]

    return "\n".join(relevant[:20])
