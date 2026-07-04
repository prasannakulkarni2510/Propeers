# SQLite is the source of truth; CSV is an export

Authoritative pipeline state lives in one local SQLite file (`pacos.db`), not in
`tracker.csv`. The same file also stores LangGraph checkpoints. A `pacos export`
command regenerates `tracker.csv` for viewing in Sheets on demand.

This **reverses the design PDF** (§7: "Every bit of state lives in tracker.csv…
No database"). We changed it because there are now three concurrent writers — the
UI/API, the scheduled inbox monitor, and long generate batches — and the old
read-whole-file / write-whole-file `tracker.csv` approach silently loses updates
when two writers overlap. SQLite gives atomic writes, and since LangGraph already
needs a checkpoint store, one local DB serves both.

`leads.csv` is unchanged: it remains the hand-editable **input** sheet, ingested
into `pacos.db`. Only derived/tracked state moved to SQLite.

_Trade-off:_ `tracker.csv` is no longer hand-editable as the source of truth — you
edit via the app/CLI, then export. We keep the "open it in Sheets" affordance as a
read-only export rather than as the live store.
