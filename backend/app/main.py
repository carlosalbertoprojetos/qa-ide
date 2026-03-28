from fastapi import FastAPI
from app.schemas import AuditRequest
from app.auditor import scan_project
from app.generator import generate_test_stub

app = FastAPI()

@app.post("/audit")
def audit(req: AuditRequest):
    issues = scan_project(req.path)
    return {"issues": issues}

@app.post("/generate-test")
def generate_test(file_path: str):
    code = generate_test_stub(file_path)
    return {"test_code": code}