from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.schemas.reports import ReportRequest, ReportResponse
from app.services.reports import ReportService


router = APIRouter(prefix="/reports", tags=["Reports API"])


@router.post("/generate", response_model=ReportResponse)
def generate_report(
    payload: ReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ReportResponse:
    service = ReportService(db, current_user.id)
    return service.generate(payload)


@router.get("/download/{filename}")
def download_report(
    filename: str,
    current_user: User = Depends(get_current_active_user),
):
    # Prevent path traversal; files are generated under REPORTS_DIR only.
    safe_name = Path(filename).name
    path = Path(settings.REPORTS_DIR) / safe_name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, filename=safe_name)
