from pathlib import Path

EXCLUDED_DIRS = {"__pycache__", "migrations", ".git", "node_modules", "venv"}


def is_test_file(path: Path) -> bool:
    name = path.name
    return name.startswith("test_") or name.endswith("_test.py")


def scan_project(path: str):
    root = Path(path)
    if not root.exists():
        return [{"file": str(root), "issue": "Caminho não existe"}]

    python_files = [p for p in root.rglob("*.py") if not any(part in EXCLUDED_DIRS for part in p.parts)]
    file_names = {p.name for p in python_files}

    issues = []
    for file_path in python_files:
        if is_test_file(file_path) or file_path.name == "__init__.py":
            continue

        base_name = file_path.stem
        test_candidates = {f"test_{base_name}.py", f"{base_name}_test.py"}

        if not test_candidates.intersection(file_names):
            issues.append({"file": str(file_path), "issue": "Sem teste automatizado"})

    return issues