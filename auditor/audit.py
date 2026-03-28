import os

EXCLUDE_DIRS = ["venv", "__pycache__", "node_modules"]

def find_python_files(base_path):
    files = []
    for root, dirs, filenames in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for f in filenames:
            if f.endswith(".py") and not f.startswith("test_"):
                files.append(os.path.join(root, f))
    return files


def has_test(file_path):
    dir_name = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)

    test_file = os.path.join(dir_name, f"test_{file_name}")
    return os.path.exists(test_file)


def audit_project(base_path):
    report = []

    files = find_python_files(base_path)

    for f in files:
        if not has_test(f):
            report.append({
                "file": f,
                "has_test": False,
                "suggested_test_file": os.path.join(
                    os.path.dirname(f),
                    f"test_{os.path.basename(f)}"
                )
            })

    return report


if __name__ == "__main__":
    import sys

    base_path = sys.argv[1] if len(sys.argv) > 1 else "."

    result = audit_project(base_path)

    if not result:
        print("Nenhum arquivo sem teste encontrado.")
    else:
        for r in result:
            print(r)