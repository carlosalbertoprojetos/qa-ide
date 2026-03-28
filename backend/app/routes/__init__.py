from fastapi import APIRouter
from app.routes.audit import router as audit_router
from app.routes.full_audit import router as full_audit_router
from app.routes.test_execution import router as test_execution_router
from app.routes.test_generation import router as test_generation_router

router = APIRouter()
router.include_router(audit_router)
router.include_router(full_audit_router)
router.include_router(test_execution_router)
router.include_router(test_generation_router)
