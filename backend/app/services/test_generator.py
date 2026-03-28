from app.agents.generator import GeneratorAgent, extract_python_code

_generator = GeneratorAgent()


def generate_tests(code: str, filename: str) -> str:
    return _generator.generate_tests(code=code, filename=filename)


def _extract_python_code(content: str) -> str:
    return extract_python_code(content)
