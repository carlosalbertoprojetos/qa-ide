from pathlib import Path
import argparse
import json

EXCLUDE_DIRS = {".git", "__pycache__", "venv", ".venv", "env", "node_modules"}
TEST_PATTERNS = ["test_", "_test", ".spec.", ".test."]


def is_test_file(path: Path) -> bool:
    return any(pattern in path.name for pattern in TEST_PATTERNS)


def find_missing_tests(root_path: Path) -> list[str]:
    missing = []
    python_files = [
        path
        for path in root_path.rglob("*.py")
        if not any(part in EXCLUDE_DIRS for part in path.parts)
    ]

    for path in python_files:
        if is_test_file(path):
            continue

        sibling_names = {f.name for f in path.parent.iterdir() if f.is_file()}
        candidate_names = {
            f"test_{path.name}",
            f"{path.stem}_test.py",
            f"{path.stem}.test.py",
            f"{path.stem}.spec.py",
        }

        if not candidate_names.intersection(sibling_names):
            missing.append(str(path.relative_to(root_path)))

    return sorted(missing)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scanner local de código para arquivos sem testes"
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Caminho da raiz do projeto a ser escaneado",
    )
    parser.add_argument("--json", action="store_true", help="Imprimir resultado em JSON")
    args = parser.parse_args()

    root_path = Path(args.root).resolve()
    missing = find_missing_tests(root_path)

    if args.json:
        print(json.dumps({"root": str(root_path), "missing_tests": missing}, ensure_ascii=False, indent=2))
        return

    print(f"Scanner de testes para: {root_path}")
    if missing:
        print("Arquivos detectados sem testes correspondentes:")
        for item in missing:
            print(f" - {item}")
    else:
        print("Nenhum arquivo sem teste encontrado.")


if __name__ == "__main__":
    main()