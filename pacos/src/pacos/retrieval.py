"""Record retrieval for the chat assistant.

Lets the chat answer questions about the operator's own data ("where am I
with Abhishek Gupta?", "who replied interested?", "what did my email to ABB
say?") from leads, tracker state, generated assets and inbox replies.

Three signals, fused:
  1. Exact entity match: a lead's full name (or first name + company, or a
     company) appearing in the question. Names are what operators ask by, and
     no embedding beats an exact match on them.
  2. Keyword search: SQLite FTS5 (BM25) over one document per lead, per asset
     and per inbox reply. Always on, works offline.
  3. Semantic search: sqlite-vec cosine KNN over NVIDIA NIM embeddings of the
     same documents, for questions phrased unlike the records ("who's keen?").
     Embedding runs in a background thread and only for changed documents, so
     a chat turn never waits on indexing; until it finishes, (1) and (2) carry.

The index lives in its own SQLite file next to tracker.db and is only ever
used to *find* leads. What the model is told about a lead is rebuilt from the
live store on every turn, so a status change shows up immediately even if its
vector is still being refreshed.
"""
from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

ASSET_LABELS = {
    "cold_email.txt": "cold email",
    "cold_dm.txt": "LinkedIn DM",
    "cover_letter.txt": "cover letter",
    "cv_notes.txt": "CV notes",
}
# Words in a question that point at one asset's text rather than the lead.
_ASSET_WORDS = {
    "cold_email.txt": {"email", "mail", "emailed"},
    "cold_dm.txt": {"dm", "linkedin", "message", "note", "inmail"},
    "cover_letter.txt": {"cover", "letter"},
    "cv_notes.txt": {"cv", "resume", "notes"},
}

_STOP = set("""
a about after all am an and any are as at be been before but by can chat could
did do does doing for from get got had has have he her him his how i if in into
is it its just last let me my now of on or our she should so status stage that
the their them there they this those to up us was we were what when where which
who whom why will with would you your position pipeline lead leads tell show find
give list going current currently doing hey please know whats where's
""".split())

# Company-name filler that shouldn't count as a company match on its own.
_COMPANY_FILLER = {"in", "india", "pvt", "ltd", "limited", "inc", "the", "and",
                   "of", "co", "llp", "private", "technologies", "solutions"}

ENGAGED = {"replied", "interested", "interview", "offer"}
STAGE_TITLES = {"needs_assets": "Needs assets", "ready": "Ready to send",
                "awaiting": "Awaiting reply", "engaged": "Engaged", "closed": "Closed"}
MAX_RECORDS = 10


def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (s or "").lower())


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


# ── how a lead reads, in words ──────────────────────────────────────────────
def lead_stage(lead: dict) -> str:
    """Same buckets as the Leads board (frontend lib/pipeline.js leadStage)."""
    status = lead.get("status") or ""
    if status in ENGAGED:
        return "engaged"
    if status == "rejected":
        return "closed"
    if status == "sent":
        return "awaiting"
    if lead.get("assets_generated") == "true":
        return "ready"
    return "needs_assets"


def follow_up_overdue(lead: dict, today: date | None = None) -> bool:
    due = lead.get("follow_up_due") or ""
    return (lead.get("status") == "sent" and bool(due)
            and due <= (today or date.today()).isoformat())


def describe_stage(lead: dict, today: date | None = None) -> str:
    """One plain sentence on where this lead is in the outreach loop."""
    status = lead.get("status") or ""
    sent, channel = lead.get("outreach_sent_date"), lead.get("channel")
    sent_bit = f"Outreach sent on {sent}" + (f" by {channel}" if channel else "") if sent else ""
    reply = lead.get("last_reply_date")
    intent = lead.get("reply_intent")
    reply_bit = (f"last reply on {reply}" + (f" ({intent})" if intent else "")) if reply else ""

    if status == "sent":
        due = lead.get("follow_up_due")
        tail = ""
        if due:
            tail = (f" Follow-up was due on {due}, so it's time to chase."
                    if follow_up_overdue(lead, today) else f" Follow up on {due} if there's no reply.")
        return f"{sent_bit or 'Marked as sent'}; no reply yet.{tail}"
    if status in ENGAGED or status == "rejected":
        parts = [p for p in (sent_bit, reply_bit) if p]
        return f"Status is {status}." + (" " + "; ".join(parts) + "." if parts else "")
    if lead.get("assets_generated") == "true":
        return "Outreach drafts are ready but nothing has been sent yet."
    if (lead.get("lead_type") or "person") == "job":
        return "Job posting with no contact person yet; nothing generated or sent."
    return "Not contacted yet; outreach drafts haven't been generated."


def record_card(lead: dict, assets: dict[str, str]) -> dict:
    """What the chat UI shows for a lead it talked about."""
    return {
        "lead_id": lead["lead_id"],
        "full_name": lead.get("full_name") or "",
        "job_title": lead.get("job_title") or "",
        "company_name": lead.get("company_name") or "",
        "city": lead.get("city") or "",
        "lead_type": lead.get("lead_type") or "person",
        "status": lead.get("status") or "",
        "stage": lead_stage(lead),
        "summary": describe_stage(lead),
        "channel": lead.get("channel") or "",
        "outreach_sent_date": lead.get("outreach_sent_date") or "",
        "last_reply_date": lead.get("last_reply_date") or "",
        "reply_intent": lead.get("reply_intent") or "",
        "follow_up_due": lead.get("follow_up_due") or "",
        "follow_up_overdue": follow_up_overdue(lead),
        "email": lead.get("predicted_email") or lead.get("email") or "",
        "email_status": lead.get("email_status") or "",
        "linkedin_url": lead.get("linkedin_url") or "",
        "assets": [ASSET_LABELS[n] for n in ASSET_LABELS if (assets.get(n) or "").strip()],
    }


def record_context(card: dict, lead: dict) -> str:
    """The model's view of one lead: every fact it may quote, labelled."""
    head = card["full_name"] or "(no contact person)"
    role = " at ".join(p for p in (card["job_title"], card["company_name"]) if p)
    lines = [f"[lead_id: {card['lead_id']}] {head}" + (f", {role}" if role else "")
             + (f" ({card['city']})" if card["city"] else "")]
    lines.append(f"  Where it stands: {card['summary']}")
    lines.append(f"  Tracker status: {card['status'] or 'none'} | Board column: {STAGE_TITLES[card['stage']]}")
    facts = {
        "Sent": card["outreach_sent_date"], "Channel": card["channel"],
        "Last reply": card["last_reply_date"], "Reply intent": card["reply_intent"],
        "Follow-up due": card["follow_up_due"],
    }
    got = " | ".join(f"{k}: {v}" for k, v in facts.items() if v)
    if got:
        lines.append(f"  {got}")
    lines.append("  Generated assets: " + (", ".join(card["assets"]) or "none yet"))
    if card["email"]:
        kind = " (predicted, not verified)" if card["email_status"] == "predicted" else ""
        lines.append(f"  Email: {card['email']}{kind}")
    if card["linkedin_url"]:
        lines.append(f"  LinkedIn: {card['linkedin_url']}")
    extra = {k: lead.get(k) for k in ("persona_tag", "domain_tag", "industry", "notes")}
    got = " | ".join(f"{k}: {v}" for k, v in extra.items() if v)
    if got:
        lines.append(f"  {got}")
    return "\n".join(lines)


# ── documents for the index ─────────────────────────────────────────────────
@dataclass
class Doc:
    doc_id: str   # lead:<id> | asset:<id>:<file> | reply:<n>
    lead_id: str  # "" for an inbox reply not tied to a lead
    kind: str     # lead | asset | reply
    text: str


def build_docs(leads: list[dict], assets: dict[str, dict[str, str]],
               replies: list[dict]) -> list[Doc]:
    docs: list[Doc] = []
    for lead in leads:
        lid = lead["lead_id"]
        la = assets.get(lid, {})
        card = record_card(lead, la)
        docs.append(Doc(f"lead:{lid}", lid, "lead", record_context(card, lead)))
        who = " at ".join(p for p in (card["full_name"], card["company_name"]) if p)
        for name, label in ASSET_LABELS.items():
            body = (la.get(name) or "").strip()
            if body:
                docs.append(Doc(f"asset:{lid}:{name}", lid, "asset",
                                f"{label.capitalize()} for {who}:\n{body[:4000]}"))
    for r in replies:
        lid = r.get("associated_lead_id") or ""
        docs.append(Doc(
            f"reply:{r['id']}", lid, "reply",
            f"Inbox reply from {r.get('sender', '')} on {r.get('received_date', '')}. "
            f"Subject: {r.get('subject', '')}. Intent: {r.get('intent', '')}."
            + (f" Linked to lead {lid}." if lid else " Not linked to any lead yet."),
        ))
    return docs


# ── the index ───────────────────────────────────────────────────────────────
class RecordIndex:
    def __init__(self, path: str | Path, embedder=None):
        self.path = Path(path)
        self.embedder = embedder
        self._lock = threading.Lock()
        self._embedding = False
        self.last_error = ""
        self.vec_supported = True
        with self._db() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS docs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT UNIQUE, lead_id TEXT, kind TEXT, text TEXT,
                    hash TEXT, vec_hash TEXT DEFAULT '');
                CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
                    text, tokenize='unicode61 remove_diacritics 2');
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
            """)

    @contextmanager
    def _db(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        try:
            c.enable_load_extension(True)
            import sqlite_vec

            sqlite_vec.load(c)
            c.enable_load_extension(False)
        except Exception as e:  # no extension support: keyword search only
            if self.vec_supported:
                log.warning("sqlite-vec unavailable, chat search is keyword-only: %s", e)
            self.vec_supported = False
        try:
            with c:
                yield c
        finally:
            c.close()

    @staticmethod
    def _meta(c, key: str) -> str:
        row = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else ""

    @property
    def _semantic(self) -> bool:
        return bool(self.vec_supported and self.embedder is not None
                    and self.embedder.available)

    def sync(self, docs: list[Doc]) -> None:
        """Make the index match `docs`; queue changed ones for embedding."""
        with self._lock, self._db() as c:
            have = {r["doc_id"]: (r["id"], r["hash"])
                    for r in c.execute("SELECT id, doc_id, hash FROM docs")}
            vec_table = self.vec_supported and bool(self._meta(c, "vec_dim"))
            want = {d.doc_id for d in docs}
            for doc_id, (rid, _) in have.items():
                if doc_id not in want:
                    c.execute("DELETE FROM docs WHERE id=?", (rid,))
                    c.execute("DELETE FROM docs_fts WHERE rowid=?", (rid,))
                    if vec_table:
                        c.execute("DELETE FROM vec_docs WHERE rowid=?", (rid,))
            for d in docs:
                h = _hash(d.text)
                old = have.get(d.doc_id)
                if old and old[1] == h:
                    continue
                if old:
                    c.execute("UPDATE docs SET text=?, hash=?, lead_id=?, kind=? WHERE id=?",
                              (d.text, h, d.lead_id, d.kind, old[0]))
                    c.execute("DELETE FROM docs_fts WHERE rowid=?", (old[0],))
                    rid = old[0]
                else:
                    rid = c.execute(
                        "INSERT INTO docs(doc_id, lead_id, kind, text, hash) VALUES (?,?,?,?,?)",
                        (d.doc_id, d.lead_id, d.kind, d.text, h)).lastrowid
                c.execute("INSERT INTO docs_fts(rowid, text) VALUES (?,?)", (rid, d.text))
        self._kick_embedding()

    def _kick_embedding(self) -> None:
        if not self._semantic or self._embedding:
            return
        self._embedding = True
        threading.Thread(target=self._embed_pending, daemon=True,
                         name="pacos-embed").start()

    def _embed_pending(self) -> None:
        try:
            with self._lock, self._db() as c:
                # A different model means different vectors: start over.
                if self._meta(c, "vec_model") != self.embedder.model:
                    c.execute("DROP TABLE IF EXISTS vec_docs")
                    c.execute("DELETE FROM meta WHERE key IN ('vec_model','vec_dim')")
                    c.execute("UPDATE docs SET vec_hash=''")
            while True:
                with self._db() as c:
                    batch = c.execute(
                        "SELECT id, text, hash FROM docs WHERE vec_hash != hash LIMIT 200"
                    ).fetchall()
                if not batch:
                    break
                vectors = self.embedder.embed([r["text"] for r in batch], "passage")
                import sqlite_vec

                with self._lock, self._db() as c:
                    if not self._meta(c, "vec_dim"):
                        dim = len(vectors[0])
                        c.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_docs USING "
                                  f"vec0(embedding float[{dim}] distance_metric=cosine)")
                        c.execute("INSERT OR REPLACE INTO meta VALUES ('vec_dim', ?)", (str(dim),))
                        c.execute("INSERT OR REPLACE INTO meta VALUES ('vec_model', ?)",
                                  (self.embedder.model,))
                    for r, v in zip(batch, vectors):
                        c.execute("DELETE FROM vec_docs WHERE rowid=?", (r["id"],))
                        c.execute("INSERT INTO vec_docs(rowid, embedding) VALUES (?,?)",
                                  (r["id"], sqlite_vec.serialize_float32(v)))
                        c.execute("UPDATE docs SET vec_hash=? WHERE id=?", (r["hash"], r["id"]))
            self.last_error = ""
        except Exception as e:  # keep chatting on keyword search; retry next sync
            self.last_error = str(e)
            log.warning("Chat index embedding stopped: %s", e)
        finally:
            self._embedding = False

    def status(self) -> dict:
        with self._db() as c:
            total = c.execute("SELECT COUNT(*) n FROM docs").fetchone()["n"]
            done = c.execute("SELECT COUNT(*) n FROM docs WHERE vec_hash = hash").fetchone()["n"]
        return {"documents": total, "embedded": done, "semantic": self._semantic,
                "embedding_now": self._embedding, "error": self.last_error}

    def search(self, query: str, k: int = 12) -> list[dict]:
        """Hybrid keyword + semantic search, fused by reciprocal rank."""
        ranked: list[list[sqlite3.Row]] = []
        terms = [t for t in _tokens(query) if t not in _STOP and len(t) > 1]
        with self._db() as c:
            if terms:
                match = " OR ".join(f'"{t}"' for t in terms)
                ranked.append(c.execute(
                    """SELECT d.id, d.doc_id, d.lead_id, d.kind FROM docs_fts f
                       JOIN docs d ON d.id = f.rowid
                       WHERE docs_fts MATCH ? ORDER BY bm25(docs_fts) LIMIT 30""",
                    (match,)).fetchall())
            if self._semantic and self._meta(c, "vec_dim"):
                try:
                    import sqlite_vec

                    qv = self.embedder.embed([query], "query")[0]
                    ranked.append(c.execute(
                        """SELECT d.id, d.doc_id, d.lead_id, d.kind FROM
                             (SELECT rowid, distance FROM vec_docs
                              WHERE embedding MATCH ? AND k = 30) v
                           JOIN docs d ON d.id = v.rowid ORDER BY v.distance""",
                        (sqlite_vec.serialize_float32(qv),)).fetchall())
                except Exception as e:
                    log.warning("Semantic search skipped: %s", e)
        scores: dict[str, float] = {}
        rows: dict[str, sqlite3.Row] = {}
        for result in ranked:
            for rank, r in enumerate(result):
                scores[r["doc_id"]] = scores.get(r["doc_id"], 0.0) + 1.0 / (60 + rank)
                rows[r["doc_id"]] = r
        best = sorted(scores, key=scores.get, reverse=True)[:k]
        return [{"doc_id": d, "lead_id": rows[d]["lead_id"], "kind": rows[d]["kind"],
                 "score": scores[d]} for d in best]


# ── entity matching ─────────────────────────────────────────────────────────
def match_leads(question: str, leads: list[dict]) -> list[tuple[dict, int]]:
    """Leads the question names. Score 3 = this person (full name, or first
    name + company), 1 = only their company, or a rare first name."""
    q = _tokens(question)
    qset = set(q)
    qtext = f" {' '.join(q)} "
    first_counts: dict[str, int] = {}
    for lead in leads:
        n = _tokens(lead.get("full_name"))
        if n:
            first_counts[n[0]] = first_counts.get(n[0], 0) + 1

    out = []
    for lead in leads:
        name = _tokens(lead.get("full_name"))
        comp = _tokens(lead.get("company_name"))
        comp_core = [t for t in comp if t not in _COMPANY_FILLER]
        company_hit = bool(comp_core) and (
            f" {' '.join(comp)} " in qtext or f" {' '.join(comp_core)} " in qtext)
        score = 0
        if len(name) >= 2 and all(t in qset for t in name):
            score = 3
        elif name and name[0] in qset and company_hit:
            score = 3
        elif company_hit:
            score = 1
        elif (name and len(name[0]) > 2 and name[0] in qset and name[0] not in _STOP
              and first_counts.get(name[0], 0) <= 3):
            score = 1
        if score:
            out.append((lead, score))
    # Someone named in full: the loose matches (same first name, same
    # company) are noise next to them.
    if any(score == 3 for _, score in out):
        return [p for p in out if p[1] == 3]
    return out


_COMPANY_PHRASE = re.compile(
    r"\b(?:from|at|@)\s+([A-Z][\w&.\-]*(?:\s+(?:[A-Z][\w&.\-]*|of|and|&))*)")


def unknown_company(question: str, leads: list[dict]) -> str:
    """A company the operator names ("Rajesh from Capgemini") that no lead
    works at, or "". Lets the chat say "not in PACOS yet" instead of
    offering someone else with the same first name."""
    for m in _COMPANY_PHRASE.finditer(question):
        phrase = m.group(1).strip(" .")
        want = {t for t in _tokens(phrase) if t not in _COMPANY_FILLER}
        if not want:
            continue
        known = False
        for l in leads:
            have = {t for t in _tokens(l.get("company_name")) if t not in _COMPANY_FILLER}
            if have and (want <= have or have <= want):
                known = True
                break
        if not known:
            return phrase
    return ""


# ── putting it together for one chat turn ───────────────────────────────────
@dataclass
class Retrieval:
    context: str = ""
    cards: dict[str, dict] = field(default_factory=dict)  # lead_id -> card, in order
    named: list[str] = field(default_factory=list)  # leads the operator named outright
    matched: list[str] = field(default_factory=list)  # named, else matched by company/first name


def retrieve(messages: list[dict], leads: list[dict], assets: dict[str, dict[str, str]],
             replies: list[dict], index: RecordIndex | None) -> Retrieval:
    asks = [m.get("content", "") for m in messages if m.get("role") == "user"]
    if not asks:
        return Retrieval()
    question = asks[-1]
    by_id = {l["lead_id"]: l for l in leads}

    matches = match_leads(question, leads)
    if not matches and len(asks) > 1:
        # "and when should I follow up?" refers back to the previous question.
        matches = [(l, min(s, 1)) for l, s in match_leads(asks[-2], leads)]
    named = [l["lead_id"] for l, s in matches if s == 3]
    company_only = [l["lead_id"] for l, s in matches if s < 3]
    missing_company = unknown_company(question, leads)
    if missing_company and not named:
        company_only = []  # a same-first-name lead elsewhere isn't who they mean

    hits = index.search(question) if index is not None else []

    chosen: list[str] = []
    for lid in named + company_only[: max(0, MAX_RECORDS - len(named))]:
        if lid not in chosen:
            chosen.append(lid)
    if not named:  # a general question: let the search pick the leads
        for h in hits:
            if len(chosen) >= MAX_RECORDS:
                break
            if h["lead_id"] in by_id and h["lead_id"] not in chosen:
                chosen.append(h["lead_id"])

    cards = {lid: record_card(by_id[lid], assets.get(lid, {})) for lid in chosen[:MAX_RECORDS]}
    blocks = [record_context(cards[lid], by_id[lid]) for lid in cards]
    if missing_company and not named:
        blocks.insert(0, f"Note: no lead in PACOS works at \"{missing_company}\". The person "
                         f"the operator mentions is not a lead yet, and any leads below are "
                         f"other people: say so, and offer to add them (attach \"lead\").")
    if len(company_only) > MAX_RECORDS - len(named) > 0:
        blocks.append(f"Note: only {MAX_RECORDS} of the {len(company_only)} leads at that "
                      f"company are listed here; say how many there are and offer to "
                      f"narrow down by name, role or city.")

    # Asset text: what the search pointed at, plus the asset the question names.
    qset = set(_tokens(question))
    excerpts = []
    wanted = [n for n, words in _ASSET_WORDS.items() if qset & words]
    for lid in list(cards)[:3]:
        for name in wanted:
            body = (assets.get(lid, {}).get(name) or "").strip()
            if body:
                excerpts.append((lid, name, body))
    for h in hits:
        if h["kind"] == "asset" and h["lead_id"] in cards and len(excerpts) < 4:
            name = h["doc_id"].rsplit(":", 1)[1]
            body = (assets.get(h["lead_id"], {}).get(name) or "").strip()
            if body and (h["lead_id"], name, body) not in excerpts:
                excerpts.append((h["lead_id"], name, body))
    for lid, name, body in excerpts[:4]:
        blocks.append(f"[{ASSET_LABELS[name]} drafted for lead_id {lid}]\n{body[:1500]}")

    reply_ids = {h["doc_id"].split(":", 1)[1] for h in hits if h["kind"] == "reply"}
    for r in replies:
        if str(r["id"]) in reply_ids or (r.get("associated_lead_id") or "") in cards:
            blocks.append(
                f"[inbox reply #{r['id']}] from {r.get('sender', '')} on "
                f"{r.get('received_date', '')}, subject \"{r.get('subject', '')}\", "
                f"intent {r.get('intent', '')}"
                + (f", linked to lead_id {r['associated_lead_id']}" if r.get("associated_lead_id")
                   else ", not linked to a lead"))

    # Always-useful pipeline lists for "who should I chase?"-style questions.
    due = [l for l in leads if follow_up_overdue(l)]
    if due:
        blocks.append("Follow-ups due today or overdue: " + "; ".join(
            f"{l.get('full_name') or l['company_name']} @ {l['company_name']} "
            f"(lead_id {l['lead_id']}, due {l['follow_up_due']})" for l in due[:15])
            + (f"; and {len(due) - 15} more" if len(due) > 15 else ""))

    matched = [lid for lid in cards if lid in named or lid in company_only]
    return Retrieval(context="\n\n".join(blocks), cards=cards, named=named, matched=matched)
