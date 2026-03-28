from openai import OpenAI, OpenAIError
from app.config import settings

client = OpenAI(api_key=settings.openai_api_key)

def audit_code(code: str) -> str:
    if not code or not code.strip():
        return "Nenhum código foi enviado para auditoria."

    prompt = (
        "Você é um engenheiro de qualidade de software. Faça uma análise de qualidade do código recebido. "
        "Responda em português e inclua:\n"
        "- principais riscos e vulnerabilidades\n"
        "- práticas de estilo e legibilidade\n"
        "- cobertura de testes e sugestões de casos de teste\n"
        "- recomendações para melhorias\n\n"
        "Código:\n"
        f"{code}\n"
    )

    try:
        response = client.chat.completions.create(
            model=settings.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )
    except OpenAIError as error:
        raise RuntimeError(f"Falha ao consultar OpenAI: {error}") from error

    choices = getattr(response, "choices", None)
    if not choices or not getattr(choices[0], "message", None):
        raise RuntimeError("Resposta inválida da API OpenAI.")

    return choices[0].message.content.strip()