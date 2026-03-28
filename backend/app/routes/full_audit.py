from fastapi import APIRouter, HTTPException

from app.schemas import FullAuditRequest, FullAuditResponse
from app.services.qa_orchestrator import run_full_audit

router = APIRouter()


@router.post("/full-audit", response_model=FullAuditResponse)
def full_audit(payload: FullAuditRequest):
    try:
        return run_full_audit(payload.code, payload.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
