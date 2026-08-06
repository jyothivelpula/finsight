"""Report generation — writes files under generated_reports/."""

from __future__ import annotations

import csv
import math
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.category import Category
from app.models.expense import Expense
from app.models.income import Income
from app.schemas.reports import ReportRequest, ReportResponse
from app.services.analytics_engine import AnalyticsEngine

# ── Premium fintech palette ──────────────────────────────────────────────
NAVY = HexColor("#0f172a")
MUTED = HexColor("#64748b")
LIGHT = HexColor("#f8fafc")
CARD_BG = HexColor("#ffffff")
BORDER = HexColor("#e2e8f0")
INDIGO = HexColor("#6366f1")
INDIGO_DARK = HexColor("#4338ca")
INDIGO_SOFT = HexColor("#eef2ff")
GREEN = HexColor("#059669")
GREEN_SOFT = HexColor("#ecfdf5")
RED = HexColor("#dc2626")
RED_SOFT = HexColor("#fef2f2")
AMBER = HexColor("#d97706")
AMBER_SOFT = HexColor("#fffbeb")
PAGE_BG = HexColor("#f1f5f9")

CHART_COLORS = [
    HexColor("#6366f1"),
    HexColor("#0ea5e9"),
    HexColor("#059669"),
    HexColor("#f59e0b"),
    HexColor("#ef4444"),
    HexColor("#8b5cf6"),
    HexColor("#14b8a6"),
    HexColor("#f97316"),
]

MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

_FONTS_READY = False
_UNICODE_FONT = False
FONT_REG = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def _register_fonts() -> None:
    global _FONTS_READY, _UNICODE_FONT, FONT_REG, FONT_BOLD
    if _FONTS_READY:
        return

    assets = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    pairs = [
        (assets / "DejaVuSans.ttf", assets / "DejaVuSans-Bold.ttf"),
        (Path(r"C:\Windows\Fonts\segoeui.ttf"), Path(r"C:\Windows\Fonts\segoeuib.ttf")),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        ),
        (Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf")),
    ]
    for regular, bold in pairs:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("FinSight", str(regular)))
            pdfmetrics.registerFont(TTFont("FinSight-Bold", str(bold)))
            FONT_REG, FONT_BOLD = "FinSight", "FinSight-Bold"
            _UNICODE_FONT = True
            _FONTS_READY = True
            return

    FONT_REG, FONT_BOLD = "Helvetica", "Helvetica-Bold"
    _UNICODE_FONT = False
    _FONTS_READY = True


def _rupee_prefix() -> str:
    _register_fonts()
    return "₹" if _UNICODE_FONT else "Rs."


def format_inr(value: Decimal | float | int | str) -> str:
    """Indian-style currency: ₹1,67,700.00"""
    amount = Decimal(str(value or 0))
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    whole_str, frac = f"{amount:.2f}".split(".")
    if len(whole_str) <= 3:
        grouped = whole_str
    else:
        last3 = whole_str[-3:]
        rest = whole_str[:-3]
        chunks: list[str] = []
        while rest:
            chunks.append(rest[-2:])
            rest = rest[:-2]
        grouped = ",".join(reversed(chunks)) + "," + last3
    return f"{sign}{_rupee_prefix()}{grouped}.{frac}"


def format_pct(value: float | int) -> str:
    return f"{float(value):.2f}%"


def health_rating(score: float) -> tuple[str, Color]:
    if score >= 85:
        return "Excellent", GREEN
    if score >= 70:
        return "Good", GREEN
    if score >= 50:
        return "Fair", AMBER
    return "Needs Attention", RED


def budget_status_label(item) -> tuple[str, Color]:
    util = float(item.utilization)
    status = (item.status or "").lower()
    if status == "exceeded" or util >= 100:
        return "Over Budget", RED
    if status in {"warning", "near_limit", "at_risk"} or util >= 80:
        return "Near Limit", AMBER
    return "On Track", GREEN


def classify_insight(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in ("exceed", "over", "warning", "used", "risk", "high")):
        return "warning"
    if any(w in lower for w in ("improv", "within", "on track", "savings", "strong", "good")):
        return "positive"
    return "recommendation"


class ReportService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.analytics = AnalyticsEngine(db, user_id)
        self.reports_dir = Path(settings.REPORTS_DIR)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, request: ReportRequest) -> ReportResponse:
        dashboard = self.analytics.build_dashboard(request.year, request.month)
        recent = self._recent_transactions(request.year, request.month or datetime.now().month)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{request.report_type}_{request.year}_{request.month or 'all'}_{stamp}.{request.format}"
        path = self.reports_dir / filename

        if request.format == "csv":
            self._write_csv(path, dashboard, request.report_type)
        elif request.format == "xlsx":
            self._write_xlsx(path, dashboard, request.report_type)
        else:
            self._write_pdf(
                path,
                dashboard,
                request.report_type,
                request.year,
                request.month,
                recent,
            )

        return ReportResponse(
            filename=filename,
            download_path=f"/api/reports/download/{filename}",
            report_type=request.report_type,
            format=request.format,
        )

    def _recent_transactions(self, year: int, month: int, limit: int = 5) -> list[dict]:
        """Latest income/expense rows for the report period (display only)."""
        start, end = self.analytics.month_bounds(year, month)
        rows: list[dict] = []

        expenses = (
            self.db.query(Expense, Category.name)
            .join(Category, Category.id == Expense.category_id)
            .filter(
                Expense.user_id == self.user_id,
                Expense.expense_date >= start,
                Expense.expense_date <= end,
            )
            .order_by(Expense.expense_date.desc(), Expense.id.desc())
            .limit(limit)
            .all()
        )
        for exp, cat_name in expenses:
            rows.append(
                {
                    "date": exp.expense_date,
                    "label": exp.merchant or exp.description or cat_name,
                    "category": cat_name,
                    "amount": exp.amount,
                    "kind": "expense",
                }
            )

        incomes = (
            self.db.query(Income)
            .filter(
                Income.user_id == self.user_id,
                Income.income_date >= start,
                Income.income_date <= end,
            )
            .order_by(Income.income_date.desc(), Income.id.desc())
            .limit(limit)
            .all()
        )
        for inc in incomes:
            rows.append(
                {
                    "date": inc.income_date,
                    "label": inc.description or inc.source,
                    "category": inc.source,
                    "amount": inc.amount,
                    "kind": "income",
                }
            )

        rows.sort(key=lambda r: (r["date"], r["kind"]), reverse=True)
        return rows[:limit]

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

    def _write_pdf(
        self,
        path: Path,
        dashboard,
        report_type: str,
        year: int,
        month: int | None,
        recent: list[dict],
    ) -> None:
        _register_fonts()
        # Two-pass so footers can show "Page X of Y".
        probe = BytesIO()
        probe_builder = _PremiumPdfBuilder(
            stream=probe,
            dashboard=dashboard,
            report_type=report_type,
            year=year,
            month=month,
            recent=recent,
            total_pages=0,
        )
        probe_builder.build()
        total_pages = probe_builder.page

        with path.open("wb") as handle:
            builder = _PremiumPdfBuilder(
                stream=handle,
                dashboard=dashboard,
                report_type=report_type,
                year=year,
                month=month,
                recent=recent,
                total_pages=total_pages,
            )
            builder.build()


class _PremiumPdfBuilder:
    """Premium 2-page FinSight Monthly Financial Report."""

    MARGIN = 36
    FOOTER_H = 42

    def __init__(
        self,
        stream,
        dashboard,
        report_type: str,
        year: int,
        month: int | None,
        recent: list[dict],
        total_pages: int,
    ):
        self.dashboard = dashboard
        self.report_type = report_type
        self.year = year
        self.month = month or datetime.now().month
        self.recent = recent
        self.total_pages = total_pages
        self.width, self.height = A4
        self.c = canvas.Canvas(stream, pagesize=A4)
        self.page = 1
        self.y = self.height - self.MARGIN
        self.generated_at = datetime.now()
        self.content_bottom = self.FOOTER_H + 14
        self.period_label = f"{MONTH_NAMES[self.month - 1]} {self.year}"

    # ── public ───────────────────────────────────────────────────────────

    def build(self) -> None:
        self._paint_page_background()
        self._draw_page1_executive()
        self._new_page(show_banner=True)
        self._draw_page2_analysis()
        self._draw_footer()
        self.c.save()

    def _draw_page1_executive(self) -> None:
        self._draw_header()
        self._draw_snapshot_cards()
        self._draw_monthly_performance()
        self._draw_income_expense_savings_chart()
        self._draw_health_section()
        self._draw_key_highlights()

    def _draw_page2_analysis(self) -> None:
        self._draw_spending_analysis()
        self._draw_budget_performance()
        self._draw_intelligence()
        self._draw_next_month_focus()
        if self.recent:
            self._draw_recent_transactions()

    # ── primitives ───────────────────────────────────────────────────────

    def _font(self, bold: bool = False, size: float = 10) -> None:
        self.c.setFont(FONT_BOLD if bold else FONT_REG, size)

    def _paint_page_background(self) -> None:
        self.c.setFillColor(PAGE_BG)
        self.c.rect(0, 0, self.width, self.height, fill=1, stroke=0)

    def _ensure(self, needed: float) -> None:
        if self.y - needed < self.content_bottom:
            self._new_page(show_banner=True)

    def _new_page(self, show_banner: bool = False) -> None:
        self._draw_footer()
        self.c.showPage()
        self.page += 1
        self._paint_page_background()
        self.y = self.height - self.MARGIN
        if show_banner:
            self._draw_continuation_banner()

    def _card(self, x, y_bottom, w, h, fill=CARD_BG, stroke=BORDER, radius=8) -> None:
        self.c.setFillColor(fill)
        self.c.setStrokeColor(stroke)
        self.c.setLineWidth(0.7)
        self.c.roundRect(x, y_bottom, w, h, radius, fill=1, stroke=1)

    def _section(self, title: str, subtitle: str | None = None) -> None:
        self._ensure(28)
        self._font(True, 12)
        self.c.setFillColor(NAVY)
        self.c.drawString(self.MARGIN, self.y, title)
        self.y -= 4
        self.c.setStrokeColor(INDIGO)
        self.c.setLineWidth(2.2)
        self.c.line(self.MARGIN, self.y, self.MARGIN + 28, self.y)
        self.y -= 12
        if subtitle:
            self._font(False, 8)
            self.c.setFillColor(MUTED)
            self.c.drawString(self.MARGIN, self.y, subtitle)
            self.y -= 12

    def _wrap(self, text: str, x: float, y: float, max_w: float, size=9, bold=False, color=NAVY, leading=None) -> float:
        leading = leading or size + 3
        self._font(bold, size)
        self.c.setFillColor(color)
        for line in simpleSplit(text, FONT_BOLD if bold else FONT_REG, size, max_w):
            self.c.drawString(x, y, line)
            y -= leading
        return y

    # ── page 1 ───────────────────────────────────────────────────────────

    def _draw_header(self) -> None:
        c = self.c
        band_h = 108
        band_y = self.height - self.MARGIN - band_h
        band_w = self.width - 2 * self.MARGIN

        c.setFillColor(INDIGO_DARK)
        c.roundRect(self.MARGIN, band_y, band_w, band_h, 12, fill=1, stroke=0)
        c.setFillColor(INDIGO)
        c.roundRect(self.MARGIN + 6, band_y + 6, band_w - 6, band_h - 12, 10, fill=1, stroke=0)

        pad = self.MARGIN + 22
        generated = self.generated_at.strftime("%d %b %Y, %I:%M %p")

        # Brand
        self._font(True, 11)
        c.setFillColor(HexColor("#c7d2fe"))
        c.drawString(pad, band_y + 82, "FinSight")

        self._font(False, 8)
        c.setFillColor(HexColor("#e0e7ff"))
        c.drawString(pad, band_y + 68, "Personal Finance Intelligence")

        # Title — own line, large, white
        self._font(True, 18)
        c.setFillColor(white)
        c.drawString(pad, band_y + 42, "Monthly Financial Report")

        # Meta
        self._font(False, 9)
        c.setFillColor(HexColor("#e0e7ff"))
        c.drawString(pad, band_y + 18, self.period_label)
        c.drawRightString(self.MARGIN + band_w - 18, band_y + 18, f"Generated {generated}")

        self.y = band_y - 18

    def _draw_continuation_banner(self) -> None:
        self._card(self.MARGIN, self.height - 58, self.width - 2 * self.MARGIN, 26, fill=INDIGO_SOFT, stroke=INDIGO_SOFT)
        self._font(True, 9)
        self.c.setFillColor(INDIGO_DARK)
        self.c.drawString(
            self.MARGIN + 12,
            self.height - 48,
            f"FinSight  ·  Financial Analysis  ·  {self.period_label}",
        )
        self.y = self.height - 72

    def _draw_snapshot_cards(self) -> None:
        self._section("Financial Snapshot", "Key metrics for the selected month")
        s = self.dashboard.summary
        score = float(s.financial_health_score)
        rating, score_color = health_rating(score)

        cards = [
            ("Total Income", format_inr(s.total_income), None, GREEN, GREEN_SOFT),
            ("Total Expenses", format_inr(s.total_expenses), None, RED, RED_SOFT),
            (
                "Net Savings",
                format_inr(s.net_savings),
                None,
                GREEN if float(s.net_savings) >= 0 else RED,
                GREEN_SOFT if float(s.net_savings) >= 0 else RED_SOFT,
            ),
            ("Health Score", f"{score:.0f}/100", rating, score_color, INDIGO_SOFT),
        ]

        gap = 10
        card_w = (self.width - 2 * self.MARGIN - 3 * gap) / 4
        card_h = 64
        self._ensure(card_h + 8)
        x = self.MARGIN
        yb = self.y - card_h
        for label, value, sub, accent, bg in cards:
            self._card(x, yb, card_w, card_h, fill=bg)
            self.c.setFillColor(accent)
            self.c.roundRect(x, yb, 4, card_h, 2, fill=1, stroke=0)
            self._font(False, 8)
            self.c.setFillColor(MUTED)
            self.c.drawString(x + 12, yb + 46, label)
            size = 12 if sub else 11
            while self.c.stringWidth(value, FONT_BOLD, size) > card_w - 22 and size > 7:
                size -= 0.5
            self._font(True, size)
            self.c.setFillColor(accent)
            self.c.drawString(x + 12, yb + (26 if sub else 20), value)
            if sub:
                self._font(False, 8)
                self.c.drawString(x + 12, yb + 12, sub)
            x += card_w + gap
        self.y = yb - 16

    def _draw_monthly_performance(self) -> None:
        self._section("Monthly Performance")
        text = self._executive_summary_text()
        lines = simpleSplit(text, FONT_REG, 9, self.width - 2 * self.MARGIN - 28)
        h = 18 + len(lines) * 12
        self._ensure(h + 6)
        yb = self.y - h
        self._card(self.MARGIN, yb, self.width - 2 * self.MARGIN, h, fill=CARD_BG)
        self._wrap(text, self.MARGIN + 14, yb + h - 14, self.width - 2 * self.MARGIN - 28, size=9, color=NAVY, leading=12)
        self.y = yb - 14

    def _executive_summary_text(self) -> str:
        s = self.dashboard.summary
        income = float(s.total_income)
        expenses = float(s.total_expenses)
        net = float(s.net_savings)
        rate = float(s.savings_rate)
        score = float(s.financial_health_score)
        rating, _ = health_rating(score)

        top = None
        if self.dashboard.expense_by_category:
            top = self.dashboard.expense_by_category[0]

        parts = [
            f"In {self.period_label}, you earned {format_inr(s.total_income)} and spent {format_inr(s.total_expenses)}, "
            f"resulting in net savings of {format_inr(s.net_savings)} ({format_pct(rate)} savings rate)."
        ]
        if top and expenses > 0:
            parts.append(
                f"Largest spend was {top.category} at {format_inr(top.amount)} ({format_pct(top.percentage)} of expenses)."
            )
        parts.append(f"Your Financial Health Score is {score:.0f}/100 ({rating}).")
        if income > 0 and net < 0:
            parts.append("Expenses exceeded income this month — prioritize high-spend categories next period.")
        elif rate >= 20:
            parts.append("Savings performance is strong relative to income.")
        return " ".join(parts)

    def _draw_income_expense_savings_chart(self) -> None:
        self._section("Income vs Expenses vs Savings")
        s = self.dashboard.summary
        income = max(float(s.total_income), 0.0)
        expenses = max(float(s.total_expenses), 0.0)
        savings = float(s.net_savings)
        chart_h = 118
        self._ensure(chart_h + 6)
        yb = self.y - chart_h
        w = self.width - 2 * self.MARGIN
        self._card(self.MARGIN, yb, w, chart_h, fill=CARD_BG)

        series = [
            ("Income", income, GREEN, format_inr(s.total_income)),
            ("Expenses", expenses, RED, format_inr(s.total_expenses)),
            ("Savings", abs(savings), GREEN if savings >= 0 else RED, format_inr(s.net_savings)),
        ]
        max_val = max(income, expenses, abs(savings), 1.0)
        bar_max = 70
        base_y = yb + 28
        gap = 18
        bar_w = 52
        start_x = self.MARGIN + 70
        usable = w - 140
        step = usable / 3

        for i, (label, value, color, display) in enumerate(series):
            cx = start_x + i * step + step / 2
            h = bar_max * (value / max_val) if max_val else 2
            self.c.setFillColor(HexColor("#e2e8f0"))
            self.c.roundRect(cx - bar_w / 2, base_y, bar_w, bar_max, 4, fill=1, stroke=0)
            self.c.setFillColor(color)
            self.c.roundRect(cx - bar_w / 2, base_y, bar_w, max(h, 3), 4, fill=1, stroke=0)
            self._font(False, 8)
            self.c.setFillColor(MUTED)
            self.c.drawCentredString(cx, base_y - 14, label)
            self._font(True, 8)
            self.c.setFillColor(color)
            self.c.drawCentredString(cx, base_y + bar_max + 6, display)

        self.y = yb - 14

    def _draw_health_section(self) -> None:
        self._section("Financial Health Score")
        s = self.dashboard.summary
        score = float(s.financial_health_score)
        rating, accent = health_rating(score)
        breakdown = self.dashboard.health_breakdown or {}
        box_h = 96
        self._ensure(box_h + 6)
        yb = self.y - box_h
        w = self.width - 2 * self.MARGIN
        self._card(self.MARGIN, yb, w, box_h, fill=CARD_BG)

        # Score badge
        cx, cy = self.MARGIN + 58, yb + box_h / 2 + 4
        self.c.setFillColor(INDIGO_SOFT)
        self.c.circle(cx, cy, 32, fill=1, stroke=0)
        self.c.setStrokeColor(accent)
        self.c.setLineWidth(3)
        self.c.circle(cx, cy, 32, fill=0, stroke=1)
        self._font(True, 18)
        self.c.setFillColor(accent)
        self.c.drawCentredString(cx, cy + 2, f"{score:.0f}")
        self._font(False, 7)
        self.c.setFillColor(MUTED)
        self.c.drawCentredString(cx, cy - 12, "/ 100")

        self._font(True, 12)
        self.c.setFillColor(NAVY)
        self.c.drawString(self.MARGIN + 108, yb + box_h - 28, f"{score:.2f} / 100")
        self._font(True, 10)
        self.c.setFillColor(accent)
        self.c.drawString(self.MARGIN + 108, yb + box_h - 44, rating)

        # Component indicators
        labels = [
            ("savings_rate", "Savings"),
            ("budget_discipline", "Budget"),
            ("expense_ratio", "Expenses"),
            ("goal_progress", "Goals"),
            ("spending_stability", "Stability"),
        ]
        chip_w = 72
        bx = self.MARGIN + 108
        by = yb + 14
        shown = 0
        for key, title in labels:
            if key not in breakdown:
                continue
            val = float(breakdown[key])
            # Components are scored out of ~20 in the engine
            pct = min(100.0, (val / 20.0) * 100.0)
            x = bx + shown * (chip_w + 8)
            self._card(x, by, chip_w, 36, fill=LIGHT, stroke=BORDER, radius=6)
            self._font(False, 7)
            self.c.setFillColor(MUTED)
            self.c.drawString(x + 6, by + 24, title)
            self._font(True, 9)
            self.c.setFillColor(NAVY)
            self.c.drawString(x + 6, by + 12, f"{val:.0f}")
            # mini bar
            self.c.setFillColor(BORDER)
            self.c.roundRect(x + 6, by + 4, chip_w - 12, 3, 1, fill=1, stroke=0)
            self.c.setFillColor(INDIGO)
            self.c.roundRect(x + 6, by + 4, max(2, (chip_w - 12) * pct / 100), 3, 1, fill=1, stroke=0)
            shown += 1

        self.y = yb - 14

    def _draw_key_highlights(self) -> None:
        self._section("Key Highlights")
        highlights = self._build_highlights()
        if not highlights:
            return
        row_h = 22
        h = 12 + len(highlights) * row_h
        self._ensure(h + 4)
        yb = self.y - h
        self._card(self.MARGIN, yb, self.width - 2 * self.MARGIN, h, fill=CARD_BG)
        y = yb + h - 16
        for kind, text in highlights:
            color = GREEN if kind == "positive" else AMBER if kind == "warning" else INDIGO
            self.c.setFillColor(color)
            self.c.circle(self.MARGIN + 16, y + 3, 3.2, fill=1, stroke=0)
            self._font(False, 9)
            self.c.setFillColor(NAVY)
            clipped = text if self.c.stringWidth(text, FONT_REG, 9) < self.width - 2 * self.MARGIN - 40 else text[:90] + "…"
            self.c.drawString(self.MARGIN + 26, y, clipped)
            y -= row_h
        self.y = yb - 10

    def _build_highlights(self) -> list[tuple[str, str]]:
        s = self.dashboard.summary
        items: list[tuple[str, str]] = []
        rate = float(s.savings_rate)
        if rate >= 20:
            items.append(("positive", f"Savings rate of {format_pct(rate)} is healthy."))
        elif float(s.total_income) > 0:
            items.append(("warning", f"Savings rate is {format_pct(rate)} — aim for 20%+ if possible."))

        if self.dashboard.expense_by_category:
            top = self.dashboard.expense_by_category[0]
            items.append(
                ("recommendation", f"Top expense category: {top.category} ({format_inr(top.amount)}, {format_pct(top.percentage)}).")
            )

        over = [b for b in self.dashboard.budget_analytics if float(b.utilization) >= 100]
        near = [b for b in self.dashboard.budget_analytics if 80 <= float(b.utilization) < 100]
        if over:
            items.append(("warning", f"{len(over)} budget(s) over limit this month."))
        elif near:
            items.append(("warning", f"{len(near)} budget(s) near the limit (>= 80% used)."))
        elif self.dashboard.budget_analytics:
            items.append(("positive", "All tracked budgets are currently on track."))

        score = float(s.financial_health_score)
        rating, _ = health_rating(score)
        items.append(("recommendation", f"Health rating: {rating} ({score:.0f}/100)."))
        return items[:5]

    # ── page 2 ───────────────────────────────────────────────────────────

    def _draw_spending_analysis(self) -> None:
        self._section("Spending Analysis", "Expense distribution by category")
        rows = list(self.dashboard.expense_by_category)
        if not rows:
            self._empty("No expenses recorded for this period.")
            return

        panel_h = 168
        self._ensure(panel_h + 6)
        yb = self.y - panel_h
        w = self.width - 2 * self.MARGIN
        self._card(self.MARGIN, yb, w, panel_h, fill=CARD_BG)

        # Donut
        self._draw_donut(self.MARGIN + 78, yb + panel_h / 2, 48, rows)

        # Category rows with bars
        list_x = self.MARGIN + 150
        list_w = w - 170
        y = yb + panel_h - 22
        for i, row in enumerate(rows[:7]):
            color = CHART_COLORS[i % len(CHART_COLORS)]
            self.c.setFillColor(color)
            self.c.circle(list_x, y + 3, 3.5, fill=1, stroke=0)
            self._font(False, 8)
            self.c.setFillColor(NAVY)
            self.c.drawString(list_x + 10, y, str(row.category)[:18])
            self._font(True, 8)
            self.c.drawRightString(list_x + list_w - 52, y, format_inr(row.amount))
            self._font(False, 8)
            self.c.setFillColor(MUTED)
            self.c.drawRightString(list_x + list_w, y, format_pct(row.percentage))
            # bar
            bar_y = y - 8
            self.c.setFillColor(LIGHT)
            self.c.roundRect(list_x + 10, bar_y, list_w - 10, 4, 2, fill=1, stroke=0)
            self.c.setFillColor(color)
            self.c.roundRect(
                list_x + 10,
                bar_y,
                max(2, (list_w - 10) * min(float(row.percentage), 100) / 100),
                4,
                2,
                fill=1,
                stroke=0,
            )
            y -= 22

        self.y = yb - 14

    def _draw_donut(self, cx: float, cy: float, radius: float, rows) -> None:
        total = sum(float(r.percentage) for r in rows) or 100.0
        start = -90.0  # start at top
        # Draw pie wedges as filled polygons approximating arcs
        for i, row in enumerate(rows[:8]):
            sweep = 360.0 * (float(row.percentage) / total)
            color = CHART_COLORS[i % len(CHART_COLORS)]
            self._wedge(cx, cy, radius, start, start + sweep, color)
            start += sweep
        # hole
        self.c.setFillColor(CARD_BG)
        self.c.circle(cx, cy, radius * 0.55, fill=1, stroke=0)
        self._font(True, 8)
        self.c.setFillColor(NAVY)
        self.c.drawCentredString(cx, cy + 2, "Spend")
        self._font(False, 7)
        self.c.setFillColor(MUTED)
        self.c.drawCentredString(cx, cy - 10, "mix")

    def _wedge(self, cx, cy, r, a0, a1, color) -> None:
        """Approximate a pie wedge with a path of line segments."""
        if a1 <= a0:
            return
        self.c.setFillColor(color)
        path = self.c.beginPath()
        path.moveTo(cx, cy)
        steps = max(4, int(abs(a1 - a0) / 6))
        for i in range(steps + 1):
            ang = math.radians(a0 + (a1 - a0) * i / steps)
            path.lineTo(cx + r * math.cos(ang), cy + r * math.sin(ang))
        path.close()
        self.c.drawPath(path, fill=1, stroke=0)

    def _draw_budget_performance(self) -> None:
        items = list(self.dashboard.budget_analytics or [])
        self._section("Budget Performance")
        if not items:
            self._empty("No budgets set for this period.")
            return

        # Table header
        header_h = 22
        row_h = 38
        need = header_h + min(len(items), 4) * row_h + 8
        self._ensure(need)
        table_w = self.width - 2 * self.MARGIN
        top = self.y
        self.c.setFillColor(INDIGO)
        self.c.roundRect(self.MARGIN, top - header_h, table_w, header_h, 6, fill=1, stroke=0)
        self._font(True, 8)
        self.c.setFillColor(white)
        cols = [
            (self.MARGIN + 10, "Category"),
            (self.MARGIN + 130, "Budget"),
            (self.MARGIN + 220, "Spent"),
            (self.MARGIN + 310, "Remaining"),
            (self.MARGIN + 400, "Used"),
            (self.MARGIN + 455, "Status"),
        ]
        for x, label in cols:
            self.c.drawString(x, top - 15, label)

        y = top - header_h
        for i, item in enumerate(items):
            self._ensure(row_h + 4)
            if self.y != y and y < self.content_bottom + row_h:
                # page broke via _ensure; redraw header context
                pass
            # if ensure created new page, self.y was reset — sync
            if y - row_h < self.content_bottom:
                self.y = y - 8
                self._ensure(row_h + header_h + 8)
                top = self.y
                self.c.setFillColor(INDIGO)
                self.c.roundRect(self.MARGIN, top - header_h, table_w, header_h, 6, fill=1, stroke=0)
                self._font(True, 8)
                self.c.setFillColor(white)
                for x, label in cols:
                    self.c.drawString(x, top - 15, label)
                y = top - header_h

            status, accent = budget_status_label(item)
            bg = LIGHT if i % 2 == 0 else CARD_BG
            self.c.setFillColor(bg)
            self.c.rect(self.MARGIN, y - row_h, table_w, row_h, fill=1, stroke=0)
            self.c.setStrokeColor(BORDER)
            self.c.setLineWidth(0.4)
            self.c.line(self.MARGIN, y - row_h, self.MARGIN + table_w, y - row_h)

            self._font(True, 8)
            self.c.setFillColor(NAVY)
            self.c.drawString(self.MARGIN + 10, y - 16, str(item.category)[:16])
            self._font(False, 8)
            self.c.drawString(self.MARGIN + 130, y - 16, format_inr(item.budget))
            self.c.drawString(self.MARGIN + 220, y - 16, format_inr(item.spent))
            self.c.drawString(self.MARGIN + 310, y - 16, format_inr(item.remaining))
            self._font(True, 8)
            self.c.setFillColor(accent)
            self.c.drawString(self.MARGIN + 400, y - 16, format_pct(item.utilization))
            self.c.drawString(self.MARGIN + 455, y - 16, status)

            # usage bar
            util = min(float(item.utilization), 100.0)
            bar_x = self.MARGIN + 10
            bar_w = table_w - 20
            self.c.setFillColor(BORDER)
            self.c.roundRect(bar_x, y - 30, bar_w, 5, 2, fill=1, stroke=0)
            self.c.setFillColor(accent)
            self.c.roundRect(bar_x, y - 30, max(2, bar_w * util / 100), 5, 2, fill=1, stroke=0)
            y -= row_h

        self.c.setStrokeColor(BORDER)
        self.c.setLineWidth(0.7)
        self.c.roundRect(self.MARGIN, y, table_w, top - y, 6, fill=0, stroke=1)
        self.y = y - 14

    def _draw_intelligence(self) -> None:
        self._section("FinSight Intelligence", "Insights from your financial activity")
        insights = [str(i).replace("\u25a0", "").strip() for i in (self.dashboard.insights or [])]
        if not insights:
            self._empty("No intelligence insights for this period.")
            return

        groups = {"positive": [], "warning": [], "recommendation": []}
        for text in insights:
            groups[classify_insight(text)].append(text)

        order = [
            ("positive", "Positive", GREEN, GREEN_SOFT),
            ("warning", "Warnings", AMBER, AMBER_SOFT),
            ("recommendation", "Recommendations", INDIGO, INDIGO_SOFT),
        ]
        for key, title, accent, bg in order:
            items = groups[key]
            if not items:
                continue
            for text in items:
                max_w = self.width - 2 * self.MARGIN - 40
                lines = simpleSplit(text, FONT_REG, 9, max_w)
                h = 28 + len(lines) * 11
                self._ensure(h + 6)
                yb = self.y - h
                self._card(self.MARGIN, yb, self.width - 2 * self.MARGIN, h, fill=bg)
                self.c.setFillColor(accent)
                self.c.roundRect(self.MARGIN, yb, 4, h, 2, fill=1, stroke=0)
                self._font(True, 8)
                self.c.drawString(self.MARGIN + 14, yb + h - 14, title)
                self._wrap(text, self.MARGIN + 14, yb + h - 28, max_w, size=9, color=NAVY, leading=11)
                self.y = yb - 8

    def _draw_next_month_focus(self) -> None:
        self._section("Next Month Focus")
        tips = self._next_month_tips()
        h = 14 + len(tips) * 18
        self._ensure(h + 6)
        yb = self.y - h
        self._card(self.MARGIN, yb, self.width - 2 * self.MARGIN, h, fill=CARD_BG)
        y = yb + h - 16
        for i, tip in enumerate(tips, 1):
            self._font(True, 8)
            self.c.setFillColor(INDIGO)
            self.c.drawString(self.MARGIN + 14, y, f"{i}.")
            self._font(False, 9)
            self.c.setFillColor(NAVY)
            self.c.drawString(self.MARGIN + 28, y, tip[:95])
            y -= 18
        self.y = yb - 12

    def _next_month_tips(self) -> list[str]:
        tips: list[str] = []
        s = self.dashboard.summary
        if self.dashboard.expense_by_category:
            top = self.dashboard.expense_by_category[0]
            tips.append(f"Review {top.category} spending — it led expenses at {format_pct(top.percentage)}.")
        over = [b for b in self.dashboard.budget_analytics if float(b.utilization) >= 100]
        near = [b for b in self.dashboard.budget_analytics if 80 <= float(b.utilization) < 100]
        if over:
            tips.append(f"Reset and tighten limits for: {', '.join(b.category for b in over[:3])}.")
        elif near:
            tips.append(f"Watch near-limit budgets: {', '.join(b.category for b in near[:3])}.")
        elif not self.dashboard.budget_analytics:
            tips.append("Set category budgets to unlock sharper spend control next month.")
        rate = float(s.savings_rate)
        if rate < 20 and float(s.total_income) > 0:
            gap = float(s.total_income) * 0.20 - float(s.net_savings)
            if gap > 0:
                tips.append(f"Target ~{format_inr(gap)} more savings to reach a 20% rate.")
        else:
            tips.append("Keep your savings habit — automate a transfer on payday if possible.")
        if float(s.financial_health_score) < 70:
            tips.append("Improve health score by reducing top discretionary categories and staying under budget.")
        return tips[:4] or ["Continue tracking income and expenses for clearer trends next month."]

    def _draw_recent_transactions(self) -> None:
        self._section("Recent Transactions", "Latest activity in this period")
        header_h, row_h = 20, 18
        h = header_h + len(self.recent) * row_h + 8
        self._ensure(h + 4)
        yb = self.y - h
        w = self.width - 2 * self.MARGIN
        self._card(self.MARGIN, yb, w, h, fill=CARD_BG)
        top = yb + h
        self.c.setFillColor(LIGHT)
        self.c.rect(self.MARGIN + 1, top - header_h - 1, w - 2, header_h, fill=1, stroke=0)
        self._font(True, 8)
        self.c.setFillColor(MUTED)
        self.c.drawString(self.MARGIN + 12, top - 14, "Date")
        self.c.drawString(self.MARGIN + 80, top - 14, "Description")
        self.c.drawString(self.MARGIN + 300, top - 14, "Category")
        self.c.drawRightString(self.MARGIN + w - 12, top - 14, "Amount")

        y = top - header_h - 14
        for tx in self.recent:
            kind = tx["kind"]
            color = GREEN if kind == "income" else RED
            sign = "+" if kind == "income" else "-"
            self._font(False, 8)
            self.c.setFillColor(MUTED)
            self.c.drawString(self.MARGIN + 12, y, tx["date"].strftime("%d %b"))
            self.c.setFillColor(NAVY)
            label = str(tx["label"] or "—")[:28]
            self.c.drawString(self.MARGIN + 80, y, label)
            self.c.setFillColor(MUTED)
            self.c.drawString(self.MARGIN + 300, y, str(tx["category"])[:16])
            self._font(True, 8)
            self.c.setFillColor(color)
            self.c.drawRightString(self.MARGIN + w - 12, y, f"{sign}{format_inr(tx['amount'])}")
            y -= row_h
        self.y = yb - 10

    def _empty(self, message: str) -> None:
        self._ensure(36)
        yb = self.y - 32
        self._card(self.MARGIN, yb, self.width - 2 * self.MARGIN, 32, fill=LIGHT)
        self._font(False, 9)
        self.c.setFillColor(MUTED)
        self.c.drawString(self.MARGIN + 14, yb + 12, message)
        self.y = yb - 12

    def _draw_footer(self) -> None:
        c = self.c
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.7)
        c.line(self.MARGIN, self.FOOTER_H + 12, self.width - self.MARGIN, self.FOOTER_H + 12)

        generated = self.generated_at.strftime("%d %b %Y")
        total = self.total_pages or self.page

        self._font(True, 7)
        c.setFillColor(INDIGO_DARK)
        c.drawString(self.MARGIN, self.FOOTER_H + 1, "FinSight • Personal Financial Intelligence")

        self._font(False, 7)
        c.setFillColor(MUTED)
        c.drawString(self.MARGIN, self.FOOTER_H - 11, f"Generated {generated}")
        c.drawCentredString(
            self.width / 2,
            self.FOOTER_H - 11,
            "Confidential • For personal financial planning",
        )
        c.drawRightString(self.width - self.MARGIN, self.FOOTER_H - 11, f"Page {self.page} of {total}")
