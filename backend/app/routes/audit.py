from fastapi import APIRouter, HTTPException
from app.schemas import AuditRequest, AuditResponse
from app.services.audit_service import audit_code

router = APIRouter()

@router.post("/audit", response_model=AuditResponse)
def audit(payload: AuditRequest):
    try:
        analysis = audit_code(payload.code)
        return {"analysis": analysis}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))