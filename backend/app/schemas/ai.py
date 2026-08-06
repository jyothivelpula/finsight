from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class AIChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)


class AIChatResponse(BaseModel):
    answer: str
    insights: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    context_summary: dict = Field(default_factory=dict)
