from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_test_with_ai(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    prompt = f"""
Você é um engenheiro de QA especialista em Python e pytest.

Analise o código abaixo e gere testes reais, úteis e executáveis com pytest.

Regras:
- Testes devem cobrir casos reais
- Não usar mocks desnecessários
- Nome do arquivo deve ser test_<nome>.py
- Código deve ser executável diretamente

Código:
{code}
"""

    response = client.chat.completions.create(
        model="gpt-5.3",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content