# QA IDE MVP

## Estrutura do projeto

- `backend/` - FastAPI backend para auditoria de código
- `scanner/` - Scanner local que identifica arquivos sem testes
- `extension/` - Extensão VSCode que envia código aberto para auditoria

## Backend

1. Acesse `backend/`
2. Crie e ative um ambiente virtual
3. Instale dependências
4. Defina `OPENAI_API_KEY` em `backend/.env`
5. Rode o backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Scanner

1. Acesse `scanner/`
2. Execute o script apontando para a raiz do projeto

```bash
cd scanner
python scanner.py ..
```

Para saída JSON:

```bash
python scanner.py .. --json
```

## Extensão VSCode

1. Acesse `extension/`
2. Instale dependências e compile

```bash
cd extension
npm install
npm run compile
```

3. No VSCode, abra a pasta `extension/` como workspace e carregue a extensão de desenvolvimento
4. Abra um arquivo qualquer e execute o comando `QA: Auditar Código`

## Teste final

- O backend deve estar rodando em `http://127.0.0.1:8000`
- A extensão enviará o código aberto ao endpoint `/audit`
- A resposta do backend será exibida no painel `QA IDE`
