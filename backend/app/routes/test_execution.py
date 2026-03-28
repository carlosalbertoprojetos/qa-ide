from fastapi import APIRouter, HTTPException

from app.schemas import RunTestsRequest, RunTestsResponse
from app.services.test_runner import run_project_tests

router = APIRouter()


@router.post("/run-tests", response_model=RunTestsResponse)
def run_tests_endpoint(payload: RunTestsRequest):
    try:
        return run_project_tests(payload.path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
