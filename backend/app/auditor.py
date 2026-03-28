import os

EXCLUDED_DIRS = ["__pycache__", "migrations", ".git", "node_modules"]

def is_test_file(filename):
    return filename.startswith("test_") or filename.endswith("_test.py")

def scan_project(path: str):
    issues = []

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for file in files:
            if file.endswith(".py") and not is_test_file(file):
                full_path = os.path.join(root, file)

                # verifica se existe teste correspondente
                test_file_1 = f"test_{file}"
                test_file_2 = file.replace(".py", "_test.py")

                if test_file_1 not in files and test_file_2 not in files:
                    issues.append({
                        "file": full_path,
                        "issue": "Sem teste automatizado"
                    })

    return issues