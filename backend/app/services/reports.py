"""Report generation — writes files under generated_reports/."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.reports import ReportRequest, ReportResponse
from app.services.analytics_engine import AnalyticsEngine


class ReportService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.analytics = AnalyticsEngine(db, user_id)
        self.reports_dir = Path(settings.REPORTS_DIR)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, request: ReportRequest) -> ReportResponse:
        dashboard = self.analytics.build_dashboard(request.year, request.month)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{request.report_type}_{request.year}_{request.month or 'all'}_{stamp}.{request.format}"
        path = self.reports_dir / filename

        if request.format == "csv":
            self._write_csv(path, dashboard, request.report_type)
        elif request.format == "xlsx":
            self._write_xlsx(path, dashboard, request.report_type)
        else:
            self._write_pdf(path, dashboard, request.report_type)

        return ReportResponse(
            filename=filename,
            download_path=f"/api/reports/download/{filename}",
            report_type=request.report_type,
            format=request.format,
        )

    def _write_csv(self, path: Path, dashboard, report_type: str) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["FinSight Report", report_type])
            writer.writerow([])
            writer.writerow(["Metric", "Value"])
            for key, value in dashboard.summary.model_dump().items():
                writer.writerow([key, value])
            writer.writerow([])
            writer.writerow(["Category", "Amount", "Percentage"])
            for row in dashboard.expense_by_category:
                writer.writerow([row.category, row.amount, row.percentage])

    def _write_xlsx(self, path: Path, dashboard, report_type: str) -> None:
        wb = Workbook()
        ws = wb.active
        ws.title = report_type.title()
        ws.append(["FinSight Report", report_type])
        ws.append([])
        ws.append(["Metric", "Value"])
        for key, value in dashboard.summary.model_dump().items():
            ws.append([key, value])
        ws.append([])
        ws.append(["Category", "Amount", "Percentage"])
        for row in dashboard.expense_by_category:
            ws.append([row.category, float(row.amount), row.percentage])
        wb.save(path)

    def _write_pdf(self, path: Path, dashboard, report_type: str) -> None:
        c = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        y = height - 50
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, f"FinSight {report_type.title()} Report")
        y -= 30
        c.setFont("Helvetica", 11)
        for key, value in dashboard.summary.model_dump().items():
            c.drawString(50, y, f"{key.replace('_', ' ').title()}: {value}")
            y -= 18
            if y < 80:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 11)
        y -= 10
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Insights")
        y -= 20
        c.setFont("Helvetica", 10)
        for insight in dashboard.insights:
            c.drawString(50, y, f"- {insight[:100]}")
            y -= 16
            if y < 80:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 10)
        c.save()
