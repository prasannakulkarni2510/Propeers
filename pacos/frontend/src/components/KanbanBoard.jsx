import { useState } from "react";

const PAGE_SIZE = 20;

// One column. Shows the first PAGE_SIZE cards and grows on demand, so a column
// holding hundreds of leads stays quick to render and scan.
function Column({ col, getId, renderCard, drag, setDrag, onMove }) {
  const [shown, setShown] = useState(PAGE_SIZE);
  const [over, setOver] = useState(false);
  const accepts = !!onMove && !!drag && drag.from !== col.id && col.droppable !== false;
  const items = col.items.slice(0, shown);

  return (
    <section
      className={`kb-col ${col.tone ? `kb-col-${col.tone}` : ""} ${accepts && over ? "kb-col-over" : ""}`}
      aria-label={`${col.title}, ${col.items.length} card${col.items.length === 1 ? "" : "s"}`}
      onDragOver={(e) => {
        if (!accepts) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        if (!over) setOver(true);
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setOver(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        if (accepts) onMove(drag.item, drag.from, col.id);
        setDrag(null);
      }}
    >
      <header className="kb-col-head">
        <span className="kb-col-title">{col.title}</span>
        <span className="kb-count">{col.items.length}</span>
      </header>
      {col.hint && <p className="kb-col-hint">{col.hint}</p>}
      <div className="kb-cards">
        {items.length === 0 && <div className="kb-empty">{col.empty || "Nothing here"}</div>}
        {items.map((item) => {
          const id = getId(item);
          return (
            <div
              key={id}
              className={`kb-card ${drag && getId(drag.item) === id ? "kb-dragging" : ""}`}
              draggable={!!onMove}
              onDragStart={(e) => {
                e.dataTransfer.effectAllowed = "move";
                e.dataTransfer.setData("text/plain", id);
                setDrag({ item, from: col.id });
              }}
              onDragEnd={() => setDrag(null)}
            >
              {renderCard(item, col.id)}
            </div>
          );
        })}
        {col.items.length > shown && (
          <button className="btn btn-ghost btn-sm kb-more" onClick={() => setShown(shown + PAGE_SIZE)}>
            Show {Math.min(PAGE_SIZE, col.items.length - shown)} more of {col.items.length - shown}
          </button>
        )}
      </div>
    </section>
  );
}

// Generic Kanban board. `columns` is [{id, title, items, hint?, tone?, empty?,
// droppable?}]. Pass `onMove(item, fromId, toId)` to make cards draggable
// between columns; without it the board is read-only and cards carry their own
// action buttons. Drag-and-drop is mouse-only, so any board with onMove should
// also offer an in-card control (e.g. a status picker) for touch and keyboard.
export default function KanbanBoard({ columns, getId, renderCard, onMove }) {
  const [drag, setDrag] = useState(null);
  return (
    <div className={`kb-board ${drag ? "kb-board-dragging" : ""}`}>
      {columns.map((col) => (
        <Column
          key={col.id}
          col={col}
          getId={getId}
          renderCard={renderCard}
          drag={drag}
          setDrag={setDrag}
          onMove={onMove}
        />
      ))}
    </div>
  );
}

// Board/List switch, remembered per page in this browser.
export function useViewMode(key, fallback = "board") {
  const storageKey = `pacos_view_${key}`;
  const [mode, setMode] = useState(() => {
    try { return localStorage.getItem(storageKey) || fallback; } catch { return fallback; }
  });
  const set = (m) => {
    setMode(m);
    try { localStorage.setItem(storageKey, m); } catch { /* not remembered */ }
  };
  return [mode, set];
}

export function ViewToggle({ mode, setMode }) {
  return (
    <div className="view-toggle" role="group" aria-label="View">
      {["board", "list"].map((m) => (
        <button
          key={m}
          className={mode === m ? "active" : ""}
          aria-pressed={mode === m}
          onClick={() => setMode(m)}
        >
          {m === "board" ? "Board" : "List"}
        </button>
      ))}
    </div>
  );
}
