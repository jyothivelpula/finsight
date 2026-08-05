from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class AIChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    # Recent turns for correction detection only — never a source of money amounts.
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)


class AIChatResponse(BaseModel):
    answer: str
    insights: list[str]
    context_summary: dict
