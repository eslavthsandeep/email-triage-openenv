"""
models.py — Typed Pydantic models for the Email Triage OpenEnv environment.
Defines Action, Observation, and Reward with full type safety.
"""

from __future__ import annotations
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ---------------------------------------------------------------------------
# Action types
# ---------------------------------------------------------------------------

class ActionType(str, Enum):
    READ        = "read"          # read full body of an email by id
    CLASSIFY    = "classify"      # classify email: spam | urgent | normal | newsletter
    REPLY       = "reply"         # draft and send a reply
    DELETE      = "delete"        # delete / mark-as-spam
    ARCHIVE     = "archive"       # archive a resolved email
    ESCALATE    = "escalate"      # escalate to a human / manager
    UNSUBSCRIBE = "unsubscribe"   # unsubscribe from newsletter sender
    SUMMARIZE   = "summarize"     # produce a triage summary report
    NOOP        = "noop"          # do nothing (wastes a step)


class Action(BaseModel):
    """Action taken by the agent each step."""
    action_type: ActionType = Field(..., description="The type of action to perform.")
    email_id: Optional[str] = Field(None, description="Target email ID (required for most actions).")
    content: Optional[str] = Field(None, description="Text content — reply body, classification label, or summary text.")

    class Config:
        use_enum_values = True


# ---------------------------------------------------------------------------
# Observation types
# ---------------------------------------------------------------------------

class EmailLabel(str, Enum):
    UNREAD      = "unread"
    SPAM        = "spam"
    URGENT      = "urgent"
    NORMAL      = "normal"
    NEWSLETTER  = "newsletter"
    ARCHIVED    = "archived"
    ESCALATED   = "escalated"


class EmailMeta(BaseModel):
    """Lightweight email header visible in the inbox listing."""
    id: str
    subject: str
    sender: str
    timestamp: str
    snippet: str               # first ~100 chars of body
    label: EmailLabel
    replied: bool = False
    read: bool = False


class InboxStats(BaseModel):
    total: int
    unread: int
    urgent: int
    spam: int
    archived: int
    escalated: int


class Observation(BaseModel):
    """Full observation returned after each step."""
    emails: List[EmailMeta] = Field(..., description="Current inbox listing (headers only).")
    open_email_body: Optional[str] = Field(None, description="Full body of the currently opened email (after READ action).")
    inbox_stats: InboxStats
    last_action_result: str = Field("", description="Human-readable result of the last action.")
    step: int = Field(0, description="Current step number.")
    done: bool = False
    task_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Reward
# ---------------------------------------------------------------------------

class Reward(BaseModel):
    """Structured reward with breakdown for transparency."""
    total: float = Field(..., ge=0.0, le=1.0, description="Aggregate reward in [0, 1].")
    classification_score: float = Field(0.0, ge=0.0, le=1.0)
    reply_quality_score: float = Field(0.0, ge=0.0, le=1.0)
    escalation_score: float = Field(0.0, ge=0.0, le=1.0)
    efficiency_score: float = Field(0.0, ge=0.0, le=1.0)
    breakdown: Dict[str, Any] = Field(default_factory=dict)
