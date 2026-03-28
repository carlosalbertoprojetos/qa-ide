import logging
import re
from pathlib import Path

from openai import OpenAI, OpenAIError

from app.config import settings

logger = logging.getLogger(__name__)


class GeneratorAgent:
    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)

    def generate_tests(
        self,
        code: str,
        filename: str,
        plan: str | None = None,
        validation_feedback: str | None = None,
        previous_tests: str | None = None,
    ) -> str:
        cleaned_code = code.strip()
        safe_filename = Path(filename).name.strip()
        if not cleaned_code:
            raise ValueError("Nenhum codigo foi enviado para gerar testes.")
        if not safe_filename:
            raise ValueError("O nome do arquivo eh obrigatorio para gerar os testes.")

        module_name = Path(safe_filename).stem
        logger.info("Generator produzindo testes para %s", safe_filename)
        prompt = self._build_prompt(
            cleaned_code=cleaned_code,
            safe_filename=safe_filename,
            module_name=module_name,
            plan=plan,
            validation_feedback=validation_feedback,
            previous_tests=previous_tests,
        )

        try:
            response = self._client.chat.completions.create(
                model=settings.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
            )
        except OpenAIError as error:
            logger.exception("Generator falhou ao consultar OpenAI")
            raise RuntimeError(f"Falha ao consultar OpenAI no generator: {error}") from error

        choices = getattr(response, "choices", None)
        if not choices or not getattr(choices[0], "message", None):
            raise RuntimeError("Resposta invalida da API OpenAI no generator.")

        content = (choices[0].message.content or "").strip()
        tests = extract_python_code(content)
        if not tests:
            raise RuntimeError("O generator retornou uma resposta vazia.")
        if "pytest" not in tests:
            raise RuntimeError("O generator nao retornou um arquivo pytest valido.")

        logger.info("Generator finalizou testes para %s", safe_filename)
        return tests

    def _build_prompt(
        self,
        *,
        cleaned_code: str,
        safe_filename: str,
        module_name: str,
        plan: str | None,
        validation_feedback: str | None,
        previous_tests: str | None,
    ) -> str:
        sections = [
            "Voce e o agente GENERATOR de um sistema multi-agent de QA.",
            "Gere um arquivo completo de testes em pytest para o codigo informado.",
            "",
            "Regras obrigatorias:",
            "- Responda somente com codigo Python puro, sem markdown e sem explicacoes.",
            "- Use pytest.",
            "- Cubra cenarios positivos, negativos e bordas relevantes.",
            "- Use mocks, monkeypatch ou patch quando houver IO, rede, subprocessos ou dependencias externas.",
            "- Inclua todos os imports necessarios.",
            "- O codigo gerado deve rodar sem ajustes manuais.",
            f"- O arquivo testado se chama {safe_filename}.",
            f"- Prefira importar com `import {module_name}` ou `from {module_name} import ...`.",
            "- Nao inclua TODO, placeholders ou comentarios desnecessarios.",
        ]

        if plan:
            sections.extend(["", "Plano do Planner:", plan.strip()])
        if previous_tests:
            sections.extend(["", "Versao anterior dos testes:", previous_tests.strip()])
        if validation_feedback:
            sections.extend(
                [
                    "",
                    "Feedback do Validator:",
                    validation_feedback.strip(),
                    "Corrija os testes com base nesses erros e retorne a nova versao completa.",
                ]
            )

        sections.extend(["", "Codigo alvo:", cleaned_code])
        return "\n".join(sections)


def extract_python_code(content: str) -> str:
    if not content:
        return ""

    fence_matches = re.findall(r"```(?:python)?\s*(.*?)```", content, flags=re.IGNORECASE | re.DOTALL)
    if fence_matches:
        return "\n\n".join(match.strip() for match in fence_matches if match.strip())

    return content.strip()
