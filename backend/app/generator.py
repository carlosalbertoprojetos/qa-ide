def generate_test_stub(file_path: str):
    file_name = file_path.split("/")[-1].replace(".py", "")

    return f"""
import pytest

def test_{file_name}_basic():
    assert True
"""