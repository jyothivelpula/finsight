"""Intent detection and amount extraction for the AI assistant."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class StatementKind(str, Enum):
    GENERAL = "general"
    GREETING = "greeting"
    AMBIGUOUS = "ambiguous"

    # User claims remaining balance is X (do NOT subtract from income)
    REMAINING_BALANCE_CLAIM = "remaining_balance_claim"

    # User spent X and wants remaining / spent from income
    REMAINING_AFTER_EXPENSE = "remaining_after_expense"

    # Plain spend statement (still compute remaining when income known)
    EXPENSE_STATEMENT = "expense_statement"

    # Hypothetical / planned spend — do not treat as confirmed transaction
    HYPOTHETICAL_EXPENSE = "hypothetical_expense"
    PLANNED_EXPENSE = "planned_expense"

    INCOME_STATEMENT = "income_statement"
    NEED = "need"
    CORRECTION = "correction"

    QUERY_REMAINING = "query_remaining"  # current_balance from DB
    QUERY_EXPENSES = "query_expenses"
    QUERY_INCOME = "query_income"  # total money / total income
    QUERY_SAVINGS = "query_savings"
    QUERY_BUDGET = "query_budget"
    QUERY_OTHER = "query_other"


@dataclass
class ParsedMessage:
    kind: StatementKind
    amounts: list[Decimal] = field(default_factory=list)
    expense_amount: Decimal | None = None
    income_amount: Decimal | None = None
    remaining_amount: Decimal | None = None
    primary_amount: Decimal | None = None
    is_correction: bool = False
    asks_remaining: bool = False
    raw: str = ""


_AMOUNT_RE = re.compile(
    r"(?:₹|rs\.?|inr)?\s*([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)

_GREETING_RE = re.compile(
    r"^\s*(hi+|hello+|hey+|hiya|yo|good\s*(morning|afternoon|evening|night)|"
    r"how\s*are\s*you(?:\s+doing)?|how'?s\s*it\s*going|what'?s\s*up|"
    r"thanks|thank\s*you|thx|bye+|goodbye|see\s*you|ok+|okay|cool|great|nice)"
    r"[\s!.?]*$",
    re.IGNORECASE,
)

_CORRECTION_RE = re.compile(
    r"\b(no+|nope|wrong|incorrect|actually|correction|i\s+meant|"
    r"not\s+\d|you'?re\s+wrong|that'?s\s+wrong)\b",
    re.IGNORECASE,
)

_ASK_REMAINING_RE = re.compile(
    r"\b("
    r"how\s+much\s+(is\s+)?(my\s+)?(money\s+)?(left|remaining)|"
    r"how\s+much\s+(money\s+)?(do\s+i\s+have\s+)?left|"
    r"how\s+much\s+(is\s+)?remaining|"
    r"what('?s|\s+is)\s+(my\s+)?remaining|"
    r"remaining\s*\??|"
    r"then\s+how\s+much|"
    r"balance\s+(left|remaining)?"
    r")\b",
    re.IGNORECASE,
)

_CLAIM_REMAINING_RE = re.compile(
    r"\b(i\s+have|i'?ve\s+got|got)\b.*\b(left|remaining|remain)\b|"
    r"\b(left|remaining)\b.*\b(is|=)\b|"
    r"^\s*i\s+have\s+(?:₹|rs\.?|inr)?\s*[0-9]",
    re.IGNORECASE,
)

_EXPENSE_RE = re.compile(
    r"\b(spent|spend|spending|paid|pay|expense|bought|purchase)\b",
    re.IGNORECASE,
)

_INCOME_WORD_RE = re.compile(
    r"\b(income|salary|total\s+(money|amount|income)|earned|earn)\b",
    re.IGNORECASE,
)

_HYPOTHETICAL_RE = re.compile(
    r"\b(what\s+if|if\s+i\s+spend|suppose|hypothetically|would\s+have)\b",
    re.IGNORECASE,
)

_PLANNED_RE = re.compile(
    r"\b(i\s+want\s+to\s+spend|want\s+to\s+spend|planning\s+to\s+spend|"
    r"i\s+plan\s+to\s+spend|thinking\s+of\s+spending)\b",
    re.IGNORECASE,
)

_NEED_RE = re.compile(
    r"\b(i\s+need|need|require|looking\s+for)\b",
    re.IGNORECASE,
)

_QUERY_INCOME_RE = re.compile(
    r"\b("
    r"total\s+(money|income|amount)|"
    r"how\s+much\s+(is\s+)?my\s+total|"
    r"how\s+much\s+(did\s+i\s+)?earn|"
    r"my\s+(total\s+)?income|"
    r"how\s+much\s+my\s+total\s+money|"
    r"show\s+(me\s+)?(my\s+)?income"
    r")\b",
    re.IGNORECASE,
)

_QUERY_EXPENSE_RE = re.compile(
    r"\b("
    r"how\s+much\s+(have\s+i\s+|did\s+i\s+)?(spend|spent)|"
    r"total\s+expense|"
    r"my\s+expenses|"
    r"how\s+much\s+spent|"
    r"show\s+(me\s+)?(my\s+)?(spending|expenses)"
    r")\b",
    re.IGNORECASE,
)

# Short follow-ups after "Income, spending, or remaining?"
_SHORT_TOPIC_RE = re.compile(
    r"^\s*(income|earning|earnings|spending|expenses?|spent|"
    r"remaining|balance|left|savings?)\s*[.!]?\s*$",
    re.IGNORECASE,
)

_ADVICE_RE = re.compile(
    r"\b("
    r"motivate|motivation|encourage|inspiring|tips?|advice|"
    r"help\s+me\s+save|how\s+(can|do|to)\s+i\s+save|"
    r"suggest|recommend|coach|remind\s+me|"
    r"tell\s+me\s+(anything|something|a\s+story)|"
    r"talk\s+to\s+me|chat\s+with\s+me"
    r")\b",
    re.IGNORECASE,
)

_OVERVIEW_RE = re.compile(
    r"\b("
    r"overview|snapshot|summary|full\s+picture|"
    r"financial\s+health|how\s+am\s+i\s+doing|"
    r"show\s+(me\s+)?(everything|my\s+finances|all)"
    r")\b",
    re.IGNORECASE,
)

_TOP_SPEND_RE = re.compile(
    r"\b("
    r"where\s+did\s+i\s+spend|"
    r"spent\s+the\s+most|"
    r"most\s+(money|spending|spend)|"
    r"top\s+(category|categories|spend|spending)|"
    r"biggest\s+(expense|category|spend)"
    r")\b",
    re.IGNORECASE,
)

_QUERY_SAVINGS_RE = re.compile(
    r"\b(how\s+much\s+(can\s+i\s+)?save|my\s+savings|net\s+savings)\b",
    re.IGNORECASE,
)


def parse_amount_token(token: str) -> Decimal:
    cleaned = token.replace(",", "").strip()
    if not cleaned or not any(ch.isdigit() for ch in cleaned):
        raise ValueError(f"Invalid amount token: {token!r}")
    return Decimal(cleaned)


def _safe_parse_amount(token: str | None) -> Decimal | None:
    if not token:
        return None
    try:
        return parse_amount_token(token)
    except Exception:
        return None


_AMOUNT_CAPTURE = r"([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]+(?:\.[0-9]+)?)"


def extract_amounts(text: str) -> list[Decimal]:
    return [parse_amount_token(m.group(1)) for m in _AMOUNT_RE.finditer(text)]


def _only_number_message(text: str, amounts: list[Decimal]) -> bool:
    if len(amounts) != 1:
        return False
    residual = re.sub(r"[₹rsINR.\s,0-9]", "", text.strip(), flags=re.IGNORECASE)
    return residual == ""


def _extract_income_and_expense(text: str, amounts: list[Decimal]) -> tuple[Decimal | None, Decimal | None]:
    """
    Prefer patterns like:
    - income is 50000 and I spent 3000
    - spent 3000 from my 50000 income
    - spent 3000 of my income (expense only)
    """
    expense: Decimal | None = None
    income: Decimal | None = None

    spent_match = re.search(
        rf"(?:spent|spend|spending|paid)\s+(?:another\s+)?(?:₹|rs\.?|inr)?\s*{_AMOUNT_CAPTURE}",
        text,
        re.IGNORECASE,
    )
    if spent_match:
        expense = _safe_parse_amount(spent_match.group(1))

    income_match = re.search(
        rf"(?:income|salary|total(?:\s+money|\s+amount)?)\s*(?:is|=|:)\s*(?:₹|rs\.?|inr)?\s*{_AMOUNT_CAPTURE}",
        text,
        re.IGNORECASE,
    )
    if income_match:
        income = _safe_parse_amount(income_match.group(1))

    from_match = re.search(
        rf"(?:from|of|out\s+of)\s+my\s+(?:₹|rs\.?|inr)?\s*{_AMOUNT_CAPTURE}\s*(?:income|salary|total)?",
        text,
        re.IGNORECASE,
    )
    if from_match and income is None:
        income = _safe_parse_amount(from_match.group(1))
    # Two amounts without clear labels: first expense-ish if "spent" present, second income
    if expense is None and income is None and len(amounts) >= 2 and _EXPENSE_RE.search(text):
        # "My income is 50000 and I spent 3000" already handled; fallback:
        if re.search(r"income.*spent|spent.*income", text, re.IGNORECASE):
            # Prefer larger as income if unlabeled
            a, b = amounts[0], amounts[1]
            income, expense = (max(a, b), min(a, b))
        else:
            expense, income = amounts[0], amounts[1]
    elif expense is None and amounts:
        if _EXPENSE_RE.search(text):
            expense = amounts[0]
        elif _INCOME_WORD_RE.search(text) and not _EXPENSE_RE.search(text):
            income = amounts[0]

    if expense is None and amounts and _EXPENSE_RE.search(text):
        expense = amounts[0]
    if income is None and len(amounts) >= 2:
        # remaining amount in list that isn't expense
        for amt in amounts:
            if expense is None or amt != expense:
                if _INCOME_WORD_RE.search(text):
                    income = amt
                    break

    return income, expense


def parse_user_message(text: str, history: list[dict] | None = None) -> ParsedMessage:
    raw = text.strip()
    amounts = extract_amounts(raw)
    history = history or []
    asks_remaining = bool(_ASK_REMAINING_RE.search(raw)) or bool(
        re.search(r"\bremaining\b", raw, re.IGNORECASE)
    )

    if not raw:
        return ParsedMessage(kind=StatementKind.GENERAL, raw=raw)

    if _GREETING_RE.match(raw) and not amounts:
        return ParsedMessage(kind=StatementKind.GREETING, raw=raw)

    if _only_number_message(raw, amounts):
        return ParsedMessage(
            kind=StatementKind.AMBIGUOUS,
            amounts=amounts,
            primary_amount=amounts[0],
            raw=raw,
        )

    is_correction = bool(_CORRECTION_RE.search(raw))
    if not is_correction and amounts and history:
        last_assistant = next(
            (m for m in reversed(history) if m.get("role") == "assistant"),
            None,
        )
        if last_assistant and extract_amounts(str(last_assistant.get("content", ""))):
            if re.search(r"^\s*no\b", raw, re.IGNORECASE):
                is_correction = True

    # Hypothetical before other spend handling
    if _HYPOTHETICAL_RE.search(raw) and amounts:
        return ParsedMessage(
            kind=StatementKind.HYPOTHETICAL_EXPENSE,
            amounts=amounts,
            expense_amount=amounts[0],
            primary_amount=amounts[0],
            asks_remaining=True,
            raw=raw,
        )

    if _PLANNED_RE.search(raw) and amounts:
        return ParsedMessage(
            kind=StatementKind.PLANNED_EXPENSE,
            amounts=amounts,
            expense_amount=amounts[0],
            primary_amount=amounts[0],
            raw=raw,
        )

    # Explicit remaining claim: "I have 3000 left" — do not subtract from income
    if amounts and _CLAIM_REMAINING_RE.search(raw) and not _EXPENSE_RE.search(raw):
        return ParsedMessage(
            kind=StatementKind.CORRECTION if is_correction else StatementKind.REMAINING_BALANCE_CLAIM,
            amounts=amounts,
            remaining_amount=amounts[0],
            primary_amount=amounts[0],
            is_correction=is_correction,
            raw=raw,
        )

    if is_correction and amounts and not _EXPENSE_RE.search(raw):
        return ParsedMessage(
            kind=StatementKind.CORRECTION,
            amounts=amounts,
            remaining_amount=amounts[0],
            primary_amount=amounts[0],
            is_correction=True,
            raw=raw,
        )

    if amounts and _NEED_RE.search(raw) and not _EXPENSE_RE.search(raw) and not asks_remaining:
        return ParsedMessage(
            kind=StatementKind.NEED,
            amounts=amounts,
            primary_amount=amounts[0],
            raw=raw,
        )

    income_amt, expense_amt = _extract_income_and_expense(raw, amounts)

    # Spent + remaining question OR spent of/from income/total
    if expense_amt is not None and (
        asks_remaining
        or _INCOME_WORD_RE.search(raw)
        or re.search(r"\b(of|from)\s+my\b", raw, re.IGNORECASE)
    ):
        return ParsedMessage(
            kind=StatementKind.REMAINING_AFTER_EXPENSE,
            amounts=amounts,
            expense_amount=expense_amt,
            income_amount=income_amt,
            primary_amount=expense_amt,
            asks_remaining=True,
            is_correction=is_correction,
            raw=raw,
        )

    # Income and spent in one message with remaining ask
    if income_amt is not None and expense_amt is not None:
        return ParsedMessage(
            kind=StatementKind.REMAINING_AFTER_EXPENSE,
            amounts=amounts,
            expense_amount=expense_amt,
            income_amount=income_amt,
            primary_amount=expense_amt,
            asks_remaining=asks_remaining or True,
            is_correction=is_correction,
            raw=raw,
        )

    if expense_amt is not None and _EXPENSE_RE.search(raw):
        # Even plain "I spent 3000" should compute remaining when possible
        return ParsedMessage(
            kind=StatementKind.REMAINING_AFTER_EXPENSE if asks_remaining else StatementKind.EXPENSE_STATEMENT,
            amounts=amounts,
            expense_amount=expense_amt,
            income_amount=income_amt,
            primary_amount=expense_amt,
            asks_remaining=asks_remaining,
            is_correction=is_correction,
            raw=raw,
        )

    if income_amt is not None and _INCOME_WORD_RE.search(raw) and not _EXPENSE_RE.search(raw):
        return ParsedMessage(
            kind=StatementKind.INCOME_STATEMENT,
            amounts=amounts,
            income_amount=income_amt,
            primary_amount=income_amt,
            is_correction=is_correction,
            raw=raw,
        )

    # Short topic picks: "income" / "spending" / "remaining"
    short = _SHORT_TOPIC_RE.match(raw)
    if short and not amounts:
        topic = short.group(1).lower()
        if topic in {"income", "earning", "earnings"}:
            return ParsedMessage(kind=StatementKind.QUERY_INCOME, raw=raw)
        if topic in {"spending", "expense", "expenses", "spent"}:
            return ParsedMessage(kind=StatementKind.QUERY_EXPENSES, raw=raw)
        if topic in {"remaining", "balance", "left"}:
            return ParsedMessage(kind=StatementKind.QUERY_REMAINING, raw=raw)
        if topic in {"saving", "savings"}:
            return ParsedMessage(kind=StatementKind.QUERY_SAVINGS, raw=raw)

    # Advice / motivation / open chat — never force a money snapshot
    if _ADVICE_RE.search(raw):
        return ParsedMessage(kind=StatementKind.GENERAL, amounts=amounts, raw=raw)

    if _TOP_SPEND_RE.search(raw):
        return ParsedMessage(kind=StatementKind.QUERY_OTHER, amounts=amounts, raw=raw)

    if _OVERVIEW_RE.search(raw):
        return ParsedMessage(kind=StatementKind.QUERY_OTHER, amounts=amounts, raw=raw)

    # Queries (no / weak amounts)
    if _QUERY_INCOME_RE.search(raw) and not _EXPENSE_RE.search(raw):
        return ParsedMessage(kind=StatementKind.QUERY_INCOME, amounts=amounts, raw=raw)

    if _QUERY_EXPENSE_RE.search(raw):
        return ParsedMessage(kind=StatementKind.QUERY_EXPENSES, amounts=amounts, raw=raw)

    if asks_remaining or re.search(
        r"how\s+much\s+money\s+do\s+i\s+have|current\s+balance|money\s+left",
        raw,
        re.IGNORECASE,
    ):
        return ParsedMessage(kind=StatementKind.QUERY_REMAINING, amounts=amounts, raw=raw)

    if _QUERY_SAVINGS_RE.search(raw):
        return ParsedMessage(kind=StatementKind.QUERY_SAVINGS, amounts=amounts, raw=raw)

    if "budget" in raw.lower():
        return ParsedMessage(kind=StatementKind.QUERY_BUDGET, amounts=amounts, raw=raw)

    if amounts and len(raw.split()) <= 4:
        return ParsedMessage(
            kind=StatementKind.AMBIGUOUS,
            amounts=amounts,
            primary_amount=amounts[0],
            raw=raw,
        )

    # Open-ended / unclear → natural chat (LLM), not a canned snapshot
    return ParsedMessage(kind=StatementKind.GENERAL, amounts=amounts, raw=raw)


def extract_context_from_history(history: list[dict] | None) -> dict:
    """
    Pull user-stated income / recent spend hints from history.
    Never overrides amounts present in the current message.
    """
    ctx: dict = {
        "user_income": None,
        "user_remaining": None,
        "last_expense": None,
        "session_expenses": [],
    }
    if not history:
        return ctx

    for msg in history:
        role = msg.get("role")
        content = str(msg.get("content", ""))
        amounts = extract_amounts(content)
        if role == "user":
            parsed = parse_user_message(content)
            if parsed.income_amount is not None:
                ctx["user_income"] = parsed.income_amount
            if parsed.kind == StatementKind.REMAINING_BALANCE_CLAIM and parsed.remaining_amount is not None:
                ctx["user_remaining"] = parsed.remaining_amount
            if parsed.expense_amount is not None and parsed.kind in {
                StatementKind.EXPENSE_STATEMENT,
                StatementKind.REMAINING_AFTER_EXPENSE,
            }:
                ctx["last_expense"] = parsed.expense_amount
                ctx["session_expenses"].append(parsed.expense_amount)
            # "yes I spent it" confirmation — keep last hypothetical as expense if present
            if re.search(r"\b(yes|yeah|yep|confirm|i\s+spent\s+it)\b", content, re.IGNORECASE):
                ctx["confirmed_last"] = True
        if role == "assistant" and amounts:
            # Remember income mentioned in verified replies
            if "income" in content.lower() and amounts:
                # Prefer largest amount tagged near income wording when possible
                m = re.search(
                    r"income[^\d₹]*?(?:₹|rs\.?)?\s*([0-9,]+)",
                    content,
                    re.IGNORECASE,
                )
                if m:
                    ctx["assistant_income"] = parse_amount_token(m.group(1))
    return ctx
