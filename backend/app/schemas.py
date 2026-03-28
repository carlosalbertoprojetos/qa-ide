from pydantic import BaseModel
from typing import List

class AuditRequest(BaseModel):
    path: str

class FileIssue(BaseModel):
    file: str
    issue: str

class AuditResponse(BaseModel):
    issues: List[FileIssue]