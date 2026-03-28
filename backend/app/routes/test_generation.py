from fastapi import APIRouter, HTTPException

from app.schemas import GenerateTestsRequest, GenerateTestsResponse
from app.services.test_generator import generate_tests

router = APIRouter()


@router.post("/generate-tests", response_model=GenerateTestsResponse)
def generate_tests_endpoint(payload: GenerateTestsRequest):
    try:
        tests = generate_tests(payload.code, payload.filename)
        return {"tests": tests}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
