import logging
from pathlib import Path

from openai import OpenAI, OpenAIError

from app.config import settings

logger = logging.getLogger(__name__)


class PlannerAgent:
    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)

    def create_test_plan(self, code: str, filename: str) -> str:
        cleaned_code = code.strip()
        safe_filename = Path(filename).name.strip()
        if not cleaned_code:
            raise ValueError("Nenhum codigo foi enviado para o planner.")
        if not safe_filename:
            raise ValueError("O nome do arquivo eh obrigatorio para o planner.")

        logger.info("Planner analisando arquivo %s", safe_filename)
        prompt = (
            "Voce e o agente PLANNER de um sistema multi-agent de QA.\n"
            "Analise o codigo recebido e gere um plano objetivo de testes em portugues.\n\n"
            "Inclua:\n"
            "1. Comportamentos principais a validar\n"
            "2. Casos positivos\n"
            "3. Casos negativos e bordas\n"
            "4. Dependencias externas que exigem mocks\n"
            "5. Estrategia de organizacao dos testes pytest\n\n"
            f"Arquivo alvo: {safe_filename}\n"
            "Responda apenas com o plano final, sem markdown.\n\n"
            "Codigo:\n"
            f"{cleaned_code}\n"
        )

        try:
            response = self._client.chat.completions.create(
                model=settings.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
            )
        except OpenAIError as error:
            logger.exception("Planner falhou ao consultar OpenAI")
            raise RuntimeError(f"Falha ao consultar OpenAI no planner: {error}") from error

        choices = getattr(response, "choices", None)
        if not choices or not getattr(choices[0], "message", None):
            raise RuntimeError("Resposta invalida da API OpenAI no planner.")

        plan = (choices[0].message.content or "").strip()
        if not plan:
            raise RuntimeError("O planner retornou um plano vazio.")

        logger.info("Planner gerou plano para %s", safe_filename)
        return plan
