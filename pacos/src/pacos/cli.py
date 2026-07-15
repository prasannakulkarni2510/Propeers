"""PACOS command-line interface (SQLite + LangGraph rebuild).

    pacos ingest                              load data/leads.csv into pacos.db
    pacos leads   [--limit N]                 preview parsed leads + domain tags
    pacos generate [--dry-run] [--limit N]    LangGraph: assets for each lead
                   [--review-hooks]           approve each hook before assets
    pacos monitor  [--days N]                 read Gmail, match replies (exact)
    pacos associate [<reply_id> <lead_id>]    list / associate unmatched replies
    pacos sent   LEAD_ID --channel email      mark an approved outreach as sent
    pacos reply  LEAD_ID --intent interested  record a recruiter reply
    pacos status LEAD_ID NEW_STATUS           move a lead along the status flow
    pacos digest                              print today's action list
    pacos export                              write tracker.csv from the store
"""
from __future__ import annotations

import sys
from datetime import datetime

from .config import Config, load
from .digest import build_digest
from .leads import load_leads
from .pipeline import Pipeline
from .store import STATUS_ORDER, PacosStore


def _parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


def _store(cfg: Config) -> PacosStore:
    store = PacosStore(cfg.db_path, database_url=cfg.database_url)
    if store.leads_empty() and cfg.leads_csv.exists():
        store.ingest_leads(load_leads(cfg.leads_csv))
    return store


def cmd_ingest(args) -> int:
    cfg = load()
    store = PacosStore(cfg.db_path, database_url=cfg.database_url)
    n = store.ingest_leads(load_leads(cfg.leads_csv))
    print(f"[ok] ingested {n} lead(s) from {cfg.leads_csv} into {cfg.db_path.name}")
    return 0


def cmd_leads(args) -> int:
    cfg = load()
    store = _store(cfg)
    rows = store.get_leads()
    if args.limit:
        rows = rows[: args.limit]
    print(f"Parsed {len(rows)} lead(s) from {cfg.db_path.name}\n")
    for r in rows:
        chan = "email+dm" if r["has_email"] else "dm-only"
        print(f"  {r['folder_name']:<28} {r['persona_tag']:<9} {r['domain_tag']:<10} {chan}")
    return 0


def cmd_generate(args) -> int:
    cfg = load()
    store = _store(cfg)
    store.ingest_leads(load_leads(cfg.leads_csv))  # sync any CSV edits
    leads = load_leads(cfg.leads_csv)
    if args.limit:
        leads = leads[: args.limit]

    pipe = Pipeline(cfg, store)
    dry = args.dry_run or pipe.dry_by_default
    if dry and not args.dry_run:
        print("[i] NVIDIA_API_KEY not set — using dry-run templates.\n")
    mode = "DRY RUN" if dry else f"Nemotron ({cfg.nemotron_model})"
    print(f"Generating assets for {len(leads)} lead(s) via {mode}"
          f"{' · review hooks' if args.review_hooks else ''}\n")

    store.reset_agent_status()
    ok = 0
    for ld in leads:
        try:
            hook = None
            if args.review_hooks:
                proposed = pipe.personalize(ld, dry_run=dry)
                print(f"\n  {ld.folder_name} — proposed hook:\n    {proposed}")
                edited = input("  Approve [Enter] or type a replacement: ").strip()
                hook = edited or proposed
            g = pipe.run_for_lead(ld, dry_run=dry, hook=hook)
            print(f"  [ok] {ld.folder_name:<28} -> {g.folder}")
            ok += 1
        except Exception as e:
            print(f"  [x]  {ld.folder_name:<28} {type(e).__name__}: {e}")

    print(f"\nDone. {ok}/{len(leads)} generated. State: {cfg.db_path}")
    print("Review output/ before sending — PACOS never sends.")
    return 0 if ok == len(leads) else 1


def cmd_monitor(args) -> int:
    cfg = load()
    store = _store(cfg)
    from .inbox_monitor import GmailUnavailable, run_monitor

    try:
        res = run_monitor(cfg, store, days=args.days)
    except GmailUnavailable as e:
        print(f"[x] {e}")
        return 1
    print(f"Scanned {res.scanned} message(s): {res.job_alerts} job alert(s), "
          f"{res.replies_classified} repl(ies) — {res.matched} matched, "
          f"{res.unmatched} unmatched.")
    if res.unmatched:
        print("Run `pacos associate` to link unmatched replies to leads.")
    return 0


def cmd_associate(args) -> int:
    cfg = load()
    store = _store(cfg)
    if not args.reply_id:
        rows = store.list_unmatched()
        if not rows:
            print("No unmatched replies.")
            return 0
        print(f"Unmatched replies ({len(rows)}):")
        for r in rows:
            print(f"  #{r['id']}  {r['sender']}  \"{r['subject'][:45]}\"  ({r['intent']})")
        print("\nAssociate with:  pacos associate <reply_id> <lead_id>")
        return 0
    ok = store.associate_reply(int(args.reply_id), args.lead_id)
    if not ok:
        print(f"[x] reply #{args.reply_id} not found")
        return 1
    print(f"[ok] reply #{args.reply_id} associated with {args.lead_id}")
    return 0


def cmd_sent(args) -> int:
    cfg = load()
    store = _store(cfg)
    if not store.mark_sent(args.lead_id, channel=args.channel,
                           sent_date=_parse_date(args.date),
                           follow_up_days=cfg.follow_up_days):
        print(f"[x] lead_id not found: {args.lead_id}")
        return 1
    print(f"[ok] {args.lead_id} sent via {args.channel}. "
          f"Follow-up due {store.get_lead(args.lead_id)['follow_up_due']}.")
    return 0


def cmd_reply(args) -> int:
    cfg = load()
    store = _store(cfg)
    if not store.mark_reply(args.lead_id, intent=args.intent, reply_date=_parse_date(args.date)):
        print(f"[x] lead_id not found: {args.lead_id}")
        return 1
    print(f"[ok] {args.lead_id} reply recorded ({args.intent}).")
    return 0


def cmd_status(args) -> int:
    cfg = load()
    store = _store(cfg)
    if not store.mark_status(args.lead_id, args.new_status):
        print(f"[x] lead_id not found: {args.lead_id}")
        return 1
    print(f"[ok] {args.lead_id} status -> {args.new_status}")
    return 0


def cmd_digest(args) -> int:
    cfg = load()
    store = _store(cfg)
    print(build_digest(cfg, store, on=_parse_date(args.on)))
    return 0


def cmd_export(args) -> int:
    cfg = load()
    store = _store(cfg)
    out = store.export_csv(cfg.tracker_csv)
    print(f"[ok] exported tracker to {out}")
    return 0


def build_parser():
    import argparse

    p = argparse.ArgumentParser(prog="pacos", description="Personal AI Career OS")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="load leads.csv into pacos.db").set_defaults(func=cmd_ingest)

    g = sub.add_parser("generate", help="LangGraph: per-lead assets")
    g.add_argument("--dry-run", action="store_true", help="templates, no API call")
    g.add_argument("--limit", type=int, default=0)
    g.add_argument("--review-hooks", action="store_true",
                   help="approve each hook before the asset agents run")
    g.set_defaults(func=cmd_generate)

    m = sub.add_parser("monitor", help="read Gmail (read-only), match replies")
    m.add_argument("--days", type=int, default=1)
    m.set_defaults(func=cmd_monitor)

    a = sub.add_parser("associate", help="list/associate unmatched replies")
    a.add_argument("reply_id", nargs="?")
    a.add_argument("lead_id", nargs="?")
    a.set_defaults(func=cmd_associate)

    s = sub.add_parser("sent", help="mark an approved outreach as sent")
    s.add_argument("lead_id")
    s.add_argument("--channel", choices=["email", "dm", "both"], required=True)
    s.add_argument("--date")
    s.set_defaults(func=cmd_sent)

    r = sub.add_parser("reply", help="record a recruiter reply")
    r.add_argument("lead_id")
    r.add_argument("--intent", choices=["interested", "rejected", "follow-up"], required=True)
    r.add_argument("--date")
    r.set_defaults(func=cmd_reply)

    st = sub.add_parser("status", help="set a lead's status")
    st.add_argument("lead_id")
    st.add_argument("new_status", choices=STATUS_ORDER + ["rejected"])
    st.set_defaults(func=cmd_status)

    d = sub.add_parser("digest", help="print today's actions")
    d.add_argument("--on")
    d.set_defaults(func=cmd_digest)

    ls = sub.add_parser("leads", help="preview parsed leads + domain tags")
    ls.add_argument("--limit", type=int, default=0)
    ls.set_defaults(func=cmd_leads)

    sub.add_parser("export", help="write tracker.csv from the store").set_defaults(func=cmd_export)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
