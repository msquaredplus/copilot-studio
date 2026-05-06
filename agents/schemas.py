"""Pydantic models for structured agent communication."""
from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class IssueStatus(str, Enum):
    PENDING = "pending"
    AWAITING_INFO = "awaiting_info"
    READY = "ready"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class TriggerType(str, Enum):
    CONVERSATION_START = "OnConversationStart"
    RECOGNIZED_INTENT = "OnRecognizedIntent"
    ERROR = "OnError"
    ACTIVITY = "OnActivity"


class ActionType(str, Enum):
    SEND_MESSAGE = "SendActivity"
    QUESTION = "Question"
    CONDITION = "ConditionGroup"
    INVOKE_CONNECTOR = "InvokeConnectorTaskAction"
    INVOKE_MCP = "InvokeExternalAgentTaskAction"
    SET_VARIABLE = "SetVariable"
    GO_TO_TOPIC = "BeginDialog"
    END_CONVERSATION = "EndDialog"


class TopicSpec(BaseModel):
    name: str
    trigger_type: TriggerType
    trigger_phrases: list[str] = Field(default_factory=list)
    description: str
    steps: list[dict[str, Any]] = Field(default_factory=list)


class ActionSpec(BaseModel):
    name: str
    action_type: ActionType
    description: str
    connector_id: str | None = None
    operation_id: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)


class AgentSpec(BaseModel):
    display_name: str
    schema_name: str
    instructions: str
    conversation_starters: list[str] = Field(default_factory=list)
    model: str = "GPT4oChat"
    language: int = 1033
    authentication_mode: str = "None"
    generative_actions_enabled: bool = True


class WorkflowRequirements(BaseModel):
    """Structured requirements extracted from an issue."""
    agent_name: str | None = None
    agent_purpose: str | None = None
    topics: list[TopicSpec] = Field(default_factory=list)
    actions: list[ActionSpec] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    variables: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_sources: list[dict[str, Any]] = Field(default_factory=list)
    auth_required: bool = False
    language: str = "en"
    raw_description: str = ""


class ClarificationQuestion(BaseModel):
    field: str
    question: str
    why_needed: str


class AnalysisResult(BaseModel):
    requirements: WorkflowRequirements
    missing_fields: list[ClarificationQuestion]
    confidence: float = Field(ge=0.0, le=1.0)
    is_complete: bool = False


class GenerationResult(BaseModel):
    issue_number: int
    files: dict[str, str]  # filename -> content
    summary: str
    warnings: list[str] = Field(default_factory=list)
