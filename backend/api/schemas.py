from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str
    role: str
    message: str
    workspace_id: str | None = None


class TasksRecommendRequest(BaseModel):
    user_id: str
    role: str
    date: str | None = None


class ProposalDraftRequest(BaseModel):
    user_id: str
    role: str
    customer: str
    purpose: str
    include_external: bool = True


class DocumentDraftRequest(BaseModel):
    user_id: str
    role: str
    document_type: str
    target_id: str | None = None


class ProductEvent(BaseModel):
    event_id: str
    user_id: str
    role: str
    screen: str
    action: str
    target_type: str | None = None
    target_id: str | None = None
    execution_id: str | None = None
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
