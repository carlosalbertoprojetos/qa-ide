import logging
import os
from fastapi import FastAPI
from dotenv import load_dotenv
from app.routes import router as api_router

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

app = FastAPI(
    title="QA IDE Backend",
    description="API de auditoria de código para a extensão QA IDE",
    version="0.1.0",
)

app.include_router(api_router)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "qa-ide backend"}


