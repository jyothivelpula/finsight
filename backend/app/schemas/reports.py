from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    report_type: str = Field(
        pattern="^(monthly|income|expense|budget|savings|health)$"
    )
    year: int = Field(ge=2000, le=2100)
    month: int | None = Field(default=None, ge=1, le=12)
    format: str = Field(default="pdf", pattern="^(pdf|xlsx|csv)$")


class ReportResponse(BaseModel):
    filename: str
    download_path: str
    report_type: str
    format: str
