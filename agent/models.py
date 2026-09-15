"""Pydantic data models and schemas for AeroTrace."""

from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field


class ErrorAnalysis(BaseModel):
    """Structured response from the agent for a technical issue."""
    is_technical_issue: bool = Field(
        description="True if the context represents a code, system, runtime, or command line error."
    )
    confidence_score: float = Field(
        default=0.9,
        description="Confidence score between 0.0 and 1.0."
    )
    issue_summary: str = Field(
        description="A concise 1-2 sentence description of what the problem is."
    )
    suggested_fix: str = Field(
        description="Immediate actionable command, code change, or step to resolve the problem."
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Optional brief question if context is insufficient."
    )
    turn_count: int = Field(
        default=1,
        description="Current multi-turn conversation turn number from memory checkpointer."
    )
    thread_id: str = Field(
        default="default_session",
        description="Active conversation session/thread ID stored in memory."
    )


class AgentState(BaseModel):
    """Unified state carrying all 3 input modalities into the agent."""
    is_enabled: bool = True
    cursor_position: Tuple[int, int] = (0, 0)
    
    # 3-Input Fusion Modalities
    screen_ocr_text: Optional[str] = None
    voice_transcript: Optional[str] = None
    mcp_app_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Decision & Resolution
    analysis: Optional[ErrorAnalysis] = None
