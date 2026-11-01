"""Pydantic models for the API surface."""
from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints, model_validator


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
    linkedin_url: str = ""
    # enrichment (auto-import from discovery) — predicted, never verified
    predicted_email: str = ""
    email_confidence: str = ""
    email_status: str = ""
    # 'person' (a real contact) or 'job' (a posting with no contact yet)
    lead_type: str = "person"
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
    job_title: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    # 'person' needs a contact (full_name + persona_tag); a 'job' is a posting
    # with no contact yet, so those two may stay empty until one is found.
    lead_type: Literal["person", "job"] = "person"
    full_name: str = ""
    persona_tag: Literal["hr", "engineer", "manager", "cto", "ceo", ""] = ""
    # recommended but allowed empty
    city: str = ""
    linkedin_url: str = ""
    # optional enrichments
    email: str = ""
    company_size: str = ""
    industry: str = ""
    company_website: str = ""
    funding_stage: str = ""

    @model_validator(mode="after")
    def _person_needs_contact(self):
        if self.lead_type == "person":
            if not self.full_name.strip():
                raise ValueError("full_name is required for a person lead")
            if not self.persona_tag:
                raise ValueError("persona_tag is required for a person lead")
        return self


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


class RegenerateAssetRequest(BaseModel):
    """Rewrite a single asset. `asset` is the filename the UI holds
    ('cold_email.txt') or the bare asset key ('cold_email')."""
    asset: str = Field(min_length=1)
    dry_run: bool = False
    # A visitor's temporary CV: grounds this rewrite only, never stored.
    cv_text: Optional[str] = Field(default=None, max_length=60_000)


class GenerateRequest(BaseModel):
    dry_run: bool = False
    limit: int = 0
    lead_id: Optional[str] = None  # generate for just one lead
    review_hooks: bool = False
    # Default: only build assets for leads that don't have them yet (so a click
    # after adding a lead builds that lead, not everyone). False rebuilds all.
    only_missing: bool = True
    # A visitor's temporary CV: grounds this run only, never stored.
    cv_text: Optional[str] = Field(default=None, max_length=60_000)


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


class EnrichRequest(DiscoveryRequest):
    """Auto-import leads from a Google X-Ray search. Inherits the discovery
    fields (company/role/city/keywords) that build the same Boolean queries.

    `pasted_html` lets the operator paste a Google X-Ray results page when the
    server-side fetch is blocked by a consent/CAPTCHA wall — the source is still
    the operator's own Google query, never a third-party people-search API."""
    pasted_html: str = ""
    max_leads: int = Field(default=25, ge=1, le=100)


class ImportedLead(BaseModel):
    lead_id: str
    full_name: str
    job_title: str
    company_name: str
    linkedin_url: str
    predicted_email: str
    email_confidence: str
    email_status: str
    created: bool


class EnrichResult(BaseModel):
    company_name: str
    profiles_found: int
    leads_imported: int
    source: str  # "browser" | "fetch" | "pasted" | "none"
    leads: list[ImportedLead] = []
    warnings: list[str] = []


class CvOut(BaseModel):
    """The base CV text that grounds asset generation. `is_sample` flags the
    shipped placeholder so the UI can warn that assets will invent facts."""
    content: str
    is_sample: bool


class CvUpdateRequest(BaseModel):
    content: str = Field(max_length=40000)


class CvExtractOut(BaseModel):
    """Text pulled from an uploaded CV file, for the operator to review."""
    content: str
    filename: str = ""


_IMAGE_URL = r"^data:image/(png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+$"
_ImageUrl = Annotated[str, StringConstraints(pattern=_IMAGE_URL, max_length=8_000_000)]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(default="", max_length=20000)
    # Screenshots on the operator's latest message, as data: URLs (~6 MB
    # each at most). Read once by the vision model and never stored.
    images: list[_ImageUrl] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def _not_empty(self):
        if not self.content.strip() and not self.images:
            raise ValueError("A message needs text or an image.")
        return self


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    # The operator's local date. The server may run on UTC, where it can
    # still be yesterday for someone in India; "today"/"yesterday" mean theirs.
    today: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    # A visitor's temporary CV: grounds drafts in this turn only, never stored.
    cv_text: Optional[str] = Field(default=None, max_length=60_000)


class ChatDraft(BaseModel):
    asset: str  # cold_email | cold_dm | cover_letter
    text: str


class ChatRecord(BaseModel):
    """A lead the chat reply talks about, with its live pipeline state."""
    lead_id: str
    full_name: str = ""
    job_title: str = ""
    company_name: str = ""
    city: str = ""
    lead_type: str = "person"
    status: str = ""
    stage: str = ""  # needs_assets | ready | awaiting | engaged | closed
    summary: str = ""
    channel: str = ""
    outreach_sent_date: str = ""
    last_reply_date: str = ""
    reply_intent: str = ""
    follow_up_due: str = ""
    follow_up_overdue: bool = False
    email: str = ""
    email_status: str = ""
    linkedin_url: str = ""
    assets: list[str] = []


class ChatChangeRequest(BaseModel):
    """An update the chat proposed and the operator confirmed (maybe edited).
    Deletes go through DELETE /api/leads/<id> instead."""
    lead_id: str
    action: Literal["sent", "reply", "status", "note"]
    channel: Literal["email", "dm", "both", ""] = ""
    intent: Literal["interested", "follow-up", "rejected", ""] = ""
    status: Literal["pending", "sent", "replied", "interested", "interview",
                    "offer", "rejected", ""] = ""
    date: str = ""
    note: str = Field(default="", max_length=500)


class ChatChange(ChatChangeRequest):
    action: Literal["sent", "reply", "status", "note", "delete"]
    lead: ChatRecord  # the lead as it is now, for the before -> after preview


class ChatResult(BaseModel):
    reply: str
    lead_proposal: Optional[ParsedLead] = None
    draft: Optional[ChatDraft] = None
    records: list[ChatRecord] = []
    change: Optional[ChatChange] = None
    # What the vision model read from the attached images, so the UI can show
    # it and later turns can refer back without resending the images.
    image_text: str = ""
    warnings: list[str] = []
    llm_used: bool
    model: str
