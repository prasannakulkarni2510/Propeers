import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { NavLink, useMatch, useNavigate } from "react-router-dom";
import Icon from "./Icon.jsx";
import { useChat } from "../store/chat";

// The row's menu is drawn at a fixed spot beside its button, so the scrolling
// list can't clip it.
function RowMenu({ chat, anchor, onClose, onRename }) {
  const star = useChat((s) => s.star);
  const remove = useChat((s) => s.remove);
  const navigate = useNavigate();
  const open = useMatch("/c/:chatId")?.params.chatId === chat.chat_id;
  const [confirming, setConfirming] = useState(false);
  const ref = useRef(null);
  const [pos, setPos] = useState(null);

  useLayoutEffect(() => {
    const r = anchor.getBoundingClientRect();
    const h = ref.current.offsetHeight;
    const w = ref.current.offsetWidth;
    setPos({
      top: Math.max(8, Math.min(r.bottom + 4, window.innerHeight - h - 8)),
      left: Math.max(8, Math.min(r.left, window.innerWidth - w - 8)),
    });
  }, [anchor, confirming]);

  useEffect(() => {
    ref.current?.querySelector("button")?.focus();
    const onDown = (e) => {
      if (!ref.current?.contains(e.target) && !anchor.contains(e.target)) onClose();
    };
    const onKey = (e) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        anchor.focus();
      }
    };
    window.addEventListener("pointerdown", onDown);
    window.addEventListener("keydown", onKey, true);
    window.addEventListener("resize", onClose);
    return () => {
      window.removeEventListener("pointerdown", onDown);
      window.removeEventListener("keydown", onKey, true);
      window.removeEventListener("resize", onClose);
    };
  }, [anchor, onClose]);

  const del = async () => {
    onClose();
    if ((await remove(chat.chat_id)) && open) navigate("/", { replace: true });
  };

  // On the body: the sidebar is its own layer, and page content would cover a menu inside it.
  return createPortal(
    <div
      ref={ref}
      className="chat-menu"
      role="menu"
      style={pos ? { top: pos.top, left: pos.left } : { visibility: "hidden" }}
    >
      {confirming ? (
        <>
          <p className="chat-menu-ask">Delete this chat? It can’t be brought back.</p>
          <button role="menuitem" className="chat-menu-danger" onClick={del}>
            <Icon name="trash" size={15} /> Yes, delete
          </button>
          <button role="menuitem" onClick={onClose}>Keep it</button>
        </>
      ) : (
        <>
          <button
            role="menuitem"
            onClick={() => {
              star(chat.chat_id, !chat.starred);
              onClose();
            }}
          >
            <Icon name={chat.starred ? "star-fill" : "star"} size={15} /> {chat.starred ? "Remove star" : "Star"}
          </button>
          <button role="menuitem" onClick={onRename}>
            <Icon name="pencil" size={15} /> Rename
          </button>
          <button role="menuitem" className="chat-menu-danger" onClick={() => setConfirming(true)}>
            <Icon name="trash" size={15} /> Delete
          </button>
        </>
      )}
    </div>,
    document.body,
  );
}

function Row({ chat, onNavigate }) {
  const rename = useChat((s) => s.rename);
  const waiting = useChat((s) => !!s.pending[chat.chat_id]);
  const [menu, setMenu] = useState(false);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(chat.title);
  const moreRef = useRef(null);
  const cancelled = useRef(false);

  const commit = () => {
    setEditing(false);
    if (!cancelled.current) rename(chat.chat_id, title);
  };

  if (editing) {
    return (
      <div className="chat-row is-editing">
        <input
          className="input chat-row-input"
          aria-label="Chat name"
          autoFocus
          maxLength={200}
          value={title}
          onFocus={(e) => e.target.select()}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "Enter") e.target.blur();
            if (e.key === "Escape") {
              cancelled.current = true;
              e.target.blur();
            }
          }}
        />
      </div>
    );
  }

  return (
    <div className={`chat-row ${menu ? "menu-open" : ""}`}>
      <NavLink
        to={`/c/${chat.chat_id}`}
        onClick={onNavigate}
        title={chat.title}
        className={({ isActive }) => `chat-row-link ${isActive ? "active" : ""}`}
      >
        {waiting ? <span className="dot running" /> : chat.starred && <Icon name="star-fill" size={12} className="chat-row-star" />}
        <span className="chat-row-title">{chat.title}</span>
      </NavLink>
      <button
        ref={moreRef}
        className="chat-row-more"
        aria-label={`Options for ${chat.title}`}
        aria-haspopup="menu"
        aria-expanded={menu}
        onClick={() => setMenu((m) => !m)}
      >
        <Icon name="more" size={16} />
      </button>
      {menu && (
        <RowMenu
          chat={chat}
          anchor={moreRef.current}
          onClose={() => setMenu(false)}
          onRename={() => {
            setMenu(false);
            cancelled.current = false;
            setTitle(chat.title);
            setEditing(true);
          }}
        />
      )}
    </div>
  );
}

// Saved chats in the sidebar: starred ones first, then the rest, newest first.
export default function ChatList({ onNavigate }) {
  const chats = useChat((s) => s.chats);
  const loadChats = useChat((s) => s.loadChats);
  const navigate = useNavigate();

  useEffect(() => {
    loadChats();
  }, [loadChats]);

  const starred = chats.filter((c) => c.starred);
  const rest = chats.filter((c) => !c.starred);

  return (
    <div className="chat-list" aria-label="Saved chats">
      <button
        className="chat-new"
        onClick={() => {
          useChat.getState().startNew();
          navigate("/");
          onNavigate();
        }}
      >
        <Icon name="plus" size={15} /> New chat
      </button>
      <div className="chat-list-scroll">
        {starred.length > 0 && (
          <>
            <div className="chat-list-label">Starred</div>
            {starred.map((c) => <Row key={c.chat_id} chat={c} onNavigate={onNavigate} />)}
          </>
        )}
        {rest.length > 0 && (
          <>
            <div className="chat-list-label">{starred.length > 0 ? "Recent" : "Chats"}</div>
            {rest.map((c) => <Row key={c.chat_id} chat={c} onNavigate={onNavigate} />)}
          </>
        )}
      </div>
    </div>
  );
}
