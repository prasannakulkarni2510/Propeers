"""Pydantic models for the API surface."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class LeadOut(BaseModel):
    lead_id: str
    full_name: str
    first_name: str
    company_name: str
    job_title: str
    city: str
    persona_tag: str
    domain_tag: str
    email: str
    has_email: bool
    folder_name: str
    # tracker-derived (empty until generated / acted on)
    status: str = ""
    assets_generated: str = ""
    outreach_sent_date: str = ""
    channel: str = ""
    last_reply_date: str = ""
    reply_intent: str = ""
    follow_up_due: str = ""
    notes: str = ""
    warnings: list[str] = []


class AddLeadRequest(BaseModel):
    # required
    full_name: str = Field(min_length=1)
    job_title: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    persona_tag: Literal["hr", "engineer", "manager", "cto", "ceo"]
    # recommended but allowed empty
    city: str = ""
    linkedin_url: str = ""
    # optional enrichments
    email: str = ""
    company_size: str = ""
    industry: str = ""
    company_website: str = ""
    funding_stage: str = ""


class ParseJDRequest(BaseModel):
    text: str = Field(min_length=30, description="Pasted job description text")


class ParsedLead(BaseModel):
    """Proposed lead fields extracted from a JD — all optional, operator edits
    and confirms before anything is written."""
    full_name: str = ""
    job_title: str = ""
    company_name: str = ""
    persona_tag: str = ""  # unlike AddLeadRequest, may be empty pre-review
    city: str = ""
    linkedin_url: str = ""
    email: str = ""
    company_size: str = ""
    industry: str = ""
    company_website: str = ""
    funding_stage: str = ""


class ParseJDResult(BaseModel):
    fields: ParsedLead
    warnings: list[str] = []
    llm_used: bool
    model: str


class AddLeadResult(BaseModel):
    lead: "LeadOut"
    created: bool
    message: str
    warnings: list[str] = []


class AssetFile(BaseModel):
    name: str
    content: str


class AssetsOut(BaseModel):
    lead_id: str
    folder_name: str
    generated: bool
    files: list[AssetFile]


class GenerateRequest(BaseModel):
    dry_run: bool = False
    limit: int = 0
    lead_id: Optional[str] = None  # generate for just one lead
    review_hooks: bool = False


class UnmatchedReply(BaseModel):
    id: int
    received_date: str
    sender: str
    subject: str
    intent: str


class AssociateRequest(BaseModel):
    reply_id: int
    lead_id: str


class GenerateResult(BaseModel):
    requested: int
    generated: int
    dry_run: bool
    model: str
    errors: list[str] = []


class SentRequest(BaseModel):
    lead_id: str
    channel: Literal["email", "dm", "both"]
    date: Optional[str] = None


class ReplyRequest(BaseModel):
    lead_id: str
    intent: Literal["interested", "rejected", "follow-up"]
    date: Optional[str] = None


class StatusRequest(BaseModel):
    lead_id: str
    status: str


class ActionResult(BaseModel):
    ok: bool
    lead_id: str
    message: str


class StatsOut(BaseModel):
    total: int
    status_counts: dict[str, int]
    followups_due: int
    with_assets: int


class AgentState(BaseModel):
    name: str
    label: str
    status: Literal["idle", "running", "done", "error"]
    detail: str = ""


class DigestOut(BaseModel):
    text: str


class JobAlertOut(BaseModel):
    date: str
    source: str
    title: str
    company: str = ""
    location: str = ""
    url: str


class ScanResult(BaseModel):
    scanned: int
    job_alerts: int
    replies_classified: int
    matched: int
    unmatched: int


class DiscoveryRequest(BaseModel):
    """Job details to hunt hiring-side people for. Company anchors the search."""
    company_name: str = Field(min_length=1)
    job_title: str = ""
    city: str = ""
    keywords: list[str] = Field(default_factory=list, max_length=8)


class DiscoveryVariant(BaseModel):
    group: str
    persona_tag: str  # lead-sheet tag a found person would carry ("" = mixed)
    query: str
    linkedin_url: str
    xray_url: str
    keywords: list[str] = []


class DiscoveryResult(BaseModel):
    company_name: str
    job_title: str = ""
    city: str = ""
    variants: list[DiscoveryVariant]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)


class ChatResult(BaseModel):
    reply: str
    lead_proposal: Optional[ParsedLead] = None
    warnings: list[str] = []
    llm_used: bool
    model: str
