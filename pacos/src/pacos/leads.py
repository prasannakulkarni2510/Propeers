"""Lead sheet loading, validation, and auto-derived columns.

The whole pipeline runs off one CSV (see design doc §4). This module reads it,
derives `first_name`, classifies `domain_tag`, and yields typed Lead objects.
No scraping — the CSV is exported/typed by the user.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "full_name",
    "job_title",
    "company_name",
    "city",
    "linkedin_url",
    "persona_tag",
]

OPTIONAL_COLUMNS = [
    "email",
    "company_size",
    "industry",
    "company_website",
    "funding_stage",
    # Enrichment (discovery auto-import): a predicted work email is never
    # treated as verified — email_status stays 'predicted' until proven.
    "predicted_email",
    "email_confidence",
    "email_status",
    # 'person' (a real contact) or 'job' (a posting with no contact yet).
    "lead_type",
]

VALID_PERSONAS = {"hr", "engineer", "manager", "cto", "ceo"}
VALID_LEAD_TYPES = {"person", "job"}

# full_name values that mean "no real person here" — such rows are job dumps.
PLACEHOLDER_NAMES = {"", "unknown", "n/a", "na", "none", "tbd", "-", "?"}


def derive_lead_type(full_name: str, explicit: str = "") -> str:
    """A placeholder name always means 'job' (there is no person to write to,
    whatever the caller claims); otherwise an explicit valid type wins."""
    if (full_name or "").strip().lower() in PLACEHOLDER_NAMES:
        return "job"
    explicit = (explicit or "").strip().lower()
    return explicit if explicit in VALID_LEAD_TYPES else "person"
VALID_DOMAINS = {"startup", "scaleup", "enterprise", "product", "services", "research"}


@dataclass
class Lead:
    full_name: str
    first_name: str
    job_title: str
    company_name: str
    city: str
    linkedin_url: str
    persona_tag: str
    domain_tag: str
    email: str = ""
    company_size: str = ""
    industry: str = ""
    company_website: str = ""
    funding_stage: str = ""
    # Enrichment fields (see OPTIONAL_COLUMNS): a predicted email is a
    # convenience, not a fact — never mark it verified.
    predicted_email: str = ""
    email_confidence: str = ""
    email_status: str = ""
    lead_type: str = "person"
    warnings: list[str] = field(default_factory=list)

    @property
    def _who(self) -> str:
        """Second half of the identity slug: the person, or (for job rows with
        no contact) the role, so two jobs at one company don't collide."""
        return self.first_name or self.job_title

    @property
    def lead_id(self) -> str:
        """Stable short id: company + first name (or role), slugified."""
        base = f"{self.company_name}-{self._who}".lower()
        return re.sub(r"[^a-z0-9]+", "-", base).strip("-")

    @property
    def folder_name(self) -> str:
        """`{company}_{first_name}` slug for the output/ directory (design §5)."""
        company = re.sub(r"[^A-Za-z0-9]+", "-", self.company_name).strip("-")
        first = re.sub(r"[^A-Za-z0-9]+", "-", self._who).strip("-")
        return f"{company}_{first}"

    @property
    def has_email(self) -> bool:
        return bool(self.email and "@" in self.email)


class LeadSheetError(RuntimeError):
    pass


def _derive_first_name(full_name: str) -> str:
    parts = str(full_name).strip().split()
    return parts[0] if parts else ""


def _to_int(value) -> int | None:
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None


def classify_domain(
    *, industry: str, company_size, funding_stage: str
) -> str:
    """Rule-based domain classifier feeding the tone system prompt (design §5/§6).

    Precedence: research signal > explicit size buckets > funding-stage buckets
    > services/product industry hints > sensible default.
    """
    industry_l = (industry or "").lower()
    funding_l = (funding_stage or "").lower()
    size = _to_int(company_size)

    # Research labs / academia / R&D — strongest, most specific signal.
    if any(k in industry_l for k in ("research", "academ", "r&d", "lab", "science")):
        return "research"

    # Explicit headcount buckets (design §6 thresholds).
    if size is not None:
        if size < 50:
            return "startup"
        if size <= 500:
            return "scaleup"
        return "enterprise"

    # Funding stage as a proxy when size is missing.
    if any(k in funding_l for k in ("pre-seed", "pre seed", "seed", "series a")):
        return "startup"
    if any(k in funding_l for k in ("series b", "series c", "series d")):
        return "scaleup"
    if any(k in funding_l for k in ("public", "ipo", "series e", "series f", "series g")):
        return "enterprise"

    # Industry hints.
    if any(k in industry_l for k in ("consult", "it services", "services", "outsourc")):
        return "services"
    if any(k in industry_l for k in ("saas", "product", "b2b")):
        return "product"

    return "scaleup"  # neutral middle-ground default


# Raw input columns, in the order leads.csv uses.
CSV_INPUT_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS


def build_lead(raw: dict, row_no: int | None = None) -> Lead:
    """Build a Lead (with derived fields + warnings) from one raw record.

    Used for both CSV rows and single leads added through the API/CLI, so the
    derivation logic lives in exactly one place.
    """
    def g(key: str) -> str:
        return str(raw.get(key, "") or "").strip()

    warnings: list[str] = []
    where = f"row {row_no}: " if row_no is not None else ""
    lead_type = derive_lead_type(g("full_name"), g("lead_type"))
    # Job rows have no contact person yet, so the person-shaped fields
    # (full_name, linkedin_url, persona_tag) are legitimately empty.
    skip_for_jobs = {"full_name", "linkedin_url", "persona_tag"}
    for col in REQUIRED_COLUMNS:
        if not g(col) and not (lead_type == "job" and col in skip_for_jobs):
            warnings.append(f"{where}empty required field '{col}'")

    persona = g("persona_tag").lower()
    if persona and persona not in VALID_PERSONAS:
        warnings.append(f"{where}persona_tag '{persona}' not in {sorted(VALID_PERSONAS)}")

    return Lead(
        full_name=g("full_name"),
        first_name=_derive_first_name(g("full_name")),
        job_title=g("job_title"),
        company_name=g("company_name"),
        city=g("city"),
        linkedin_url=g("linkedin_url"),
        persona_tag=persona,
        domain_tag=classify_domain(
            industry=g("industry"), company_size=g("company_size"),
            funding_stage=g("funding_stage")),
        email=g("email"),
        company_size=g("company_size"),
        industry=g("industry"),
        company_website=g("company_website"),
        funding_stage=g("funding_stage"),
        predicted_email=g("predicted_email"),
        email_confidence=g("email_confidence"),
        email_status=g("email_status"),
        lead_type=lead_type,
        warnings=warnings,
    )


def append_lead_to_csv(csv_path: str | Path, raw: dict) -> bool:
    """Append a lead to leads.csv, keeping the input file in sync with the store.

    Returns True if a new row was written, False if that lead_id already exists
    in the file (the DB upsert handles edits; we don't duplicate CSV rows).
    """
    import csv

    csv_path = Path(csv_path)
    new_id = build_lead(raw).lead_id
    existing_ids: set[str] = set()
    if csv_path.exists():
        # Upgrade an older header in place first: a sheet written before the
        # enrichment columns existed has fewer columns than CSV_INPUT_COLUMNS,
        # and appending a full-width row under a short header corrupts the file.
        _ensure_csv_columns(csv_path)
        for ld in load_leads(csv_path):
            existing_ids.add(ld.lead_id)
    if new_id in existing_ids:
        return False

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_INPUT_COLUMNS, extrasaction="ignore")
        if write_header:
            w.writeheader()
        w.writerow({c: str(raw.get(c, "") or "").strip() for c in CSV_INPUT_COLUMNS})
    return True


def _ensure_csv_columns(csv_path: Path) -> None:
    """Rewrite leads.csv with the full CSV_INPUT_COLUMNS header when it predates
    newer optional columns, so appended rows stay aligned. No-op when current."""
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False).fillna("")
    df.columns = [c.strip() for c in df.columns]
    if all(col in df.columns for col in CSV_INPUT_COLUMNS):
        return
    for col in CSV_INPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df[CSV_INPUT_COLUMNS].to_csv(csv_path, index=False)


def remove_lead_from_csv(csv_path: str | Path, lead_id: str) -> bool:
    """Rewrite leads.csv without the given lead, keeping the input file in
    sync with the store on delete (the mirror of append_lead_to_csv).
    Returns True if a row was removed; a missing file is nothing to do."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return False
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False).fillna("")
    df.columns = [c.strip() for c in df.columns]
    keep = [i for i, row in df.iterrows()
            if build_lead(row.to_dict()).lead_id != lead_id]
    if len(keep) == len(df):
        return False
    df.loc[keep].to_csv(csv_path, index=False)
    return True


def load_leads(csv_path: str | Path) -> list[Lead]:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise LeadSheetError(f"Lead sheet not found: {csv_path}")

    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False).fillna("")
    df.columns = [c.strip() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise LeadSheetError(
            f"Lead sheet {csv_path} is missing required columns: {', '.join(missing)}"
        )

    leads: list[Lead] = []
    for i, row in df.iterrows():
        leads.append(build_lead(row.to_dict(), row_no=i + 2))
    return leads
