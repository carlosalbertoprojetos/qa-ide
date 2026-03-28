from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class AuditRequest(BaseModel):
    file_path: str
    code: str

@app.post("/generate-tests")
def generate_tests(req: AuditRequest):
    prompt = f"""
Você é um engenheiro de QA especialista.

Gere testes para o código abaixo.

Regras:
- Use pytest
- Cubra casos principais e edge cases
- Código limpo e executável

Arquivo: {req.file_path}

Código:
{req.code}
"""

    response = client.chat.completions.create(
        model="gpt-5.3",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return {"tests": response.choices[0].message.content}