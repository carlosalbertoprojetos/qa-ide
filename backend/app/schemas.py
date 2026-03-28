from pydantic import BaseModel


class AuditRequest(BaseModel):
    code: str


class AuditResponse(BaseModel):
    analysis: str


class GenerateTestsRequest(BaseModel):
    code: str
    filename: str


class GenerateTestsResponse(BaseModel):
    tests: str


class RunTestsRequest(BaseModel):
    path: str


class RunTestsResponse(BaseModel):
    success: bool
    output: str
    errors: str


class FullAuditRequest(BaseModel):
    code: str
    filename: str


class FullAuditAttempt(BaseModel):
    attempt: int
    success: bool
    output: str
    errors: str
    corrected: bool


class FullAuditResult(BaseModel):
    success: bool
    auto_corrected: bool
    total_attempts: int
    attempts: list[FullAuditAttempt]


class FullAuditResponse(BaseModel):
    plan: str
    tests: str
    result: FullAuditResult
    fixed_tests: str
    history_path: str
    created_at: str
