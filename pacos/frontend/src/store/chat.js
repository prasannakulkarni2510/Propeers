// The chat: the conversation on screen and the list of saved ones.
// Chats live on the server, so they follow the operator across devices and
// survive a reload. Images are the exception: they are read once and never
// stored, so a saved message keeps only how many it had and the text read.
import { create } from "zustand";
import { api } from "../services/api";
import { useStore } from "./index";

const READ_LABEL = "[Attached screenshot, as read by the vision model]";

// Server limits (backend/models.py): 20000 characters per message and 40
// messages per request. A long paste plus the text read from its screenshot
// can exceed the first; the image text is kept, the typed text trimmed.
const MAX_CONTENT = 20000;
const MAX_TURNS = 40;

const forModel = (m) => {
  if (!m.imageText) return { role: m.role, content: m.content.slice(0, MAX_CONTENT) };
  const read = `${READ_LABEL}\n${m.imageText}`.slice(0, MAX_CONTENT);
  const room = MAX_CONTENT - read.length - 2;
  const typed = room > 0 ? m.content.slice(0, room) : "";
  return { role: m.role, content: [typed, read].filter(Boolean).join("\n\n") };
};

const forSaving = (messages) =>
  messages.map(({ images, ...m }) => (images?.length ? { ...m, imageCount: images.length } : m));

const titleFrom = (content) => {
  const line = content.split("\n").find((l) => l.trim()) || "";
  const clean = line.replace(/\s+/g, " ").trim();
  if (!clean) return "Screenshot";
  return clean.length > 60 ? `${clean.slice(0, 57).trimEnd()}…` : clean;
};

const summary = ({ messages, ...chat }) => chat;

// Writes for one chat go out one after another, so an older save can never
// land on top of a newer one.
const queues = {};
let warned = false;
const save = (id, messages) => {
  const body = { messages: forSaving(messages) };
  const run = () =>
    api.updateChat(id, body).catch((e) => {
      if (e.status === 404 || warned) return; // deleted meanwhile, or already said
      warned = true;
      useStore.getState().setToast(`This chat isn't being saved: ${e.message}`);
    });
  queues[id] = (queues[id] || Promise.resolve()).then(run);
  return queues[id];
};

export const useChat = create((set, get) => ({
  chats: [], // saved chats without their messages, newest first
  chatId: null, // null: a new chat that has no message yet
  // {role, content, images?, imageCount?, imageText?, proposal?, warnings?,
  //  draft?, records?, change?, changeState?, changeResult?, removed?, added?}
  messages: [],
  loading: false, // opening a saved chat
  pending: {}, // chat ids waiting on a reply ("new" until the chat has an id)
  view: 0, // goes up whenever a different conversation is put on screen
  input: "",
  attachments: [], // data: URLs waiting to be sent with the next message

  setInput: (input) => set({ input }),
  setAttachments: (attachments) => set({ attachments }),

  loadChats: async () => {
    try {
      set({ chats: await api.chats() });
    } catch {
      /* the list is a convenience; the chat itself still works */
    }
  },

  startNew: () => set((s) => ({ chatId: null, messages: [], loading: false, view: s.view + 1 })),

  // Put a saved chat on screen. Resolves false when it no longer exists.
  open: async (id) => {
    if (get().chatId === id) return true;
    set((s) => ({ chatId: id, messages: [], loading: true, view: s.view + 1 }));
    try {
      const chat = await api.getChat(id);
      if (get().chatId === id) set({ messages: chat.messages || [], loading: false });
      return true;
    } catch (e) {
      if (get().chatId !== id) return true;
      get().startNew();
      useStore.getState().setToast(e.status === 404 ? "That chat was deleted." : `Couldn't open that chat: ${e.message}`);
      return false;
    }
  },

  // Card actions write into the stored message so the outcome ("added",
  // "saved") is still there when the chat is reopened.
  patch: (i, fn) => {
    const messages = get().messages.map((m, j) => (j === i ? { ...m, ...fn(m) } : m));
    set({ messages });
    if (get().chatId) save(get().chatId, messages);
  },

  // Send what is typed. `onCreated(id)` fires when a new chat gets its id.
  send: async (onCreated) => {
    const { input, attachments, messages, chatId, pending, view } = get();
    const content = input.trim();
    if ((!content && !attachments.length) || pending[chatId || "new"]) return;
    const mine = { role: "user", content, images: attachments };
    const history = [...messages, mine];
    const setPending = (key, on) =>
      set((s) => {
        const next = { ...s.pending };
        if (on) next[key] = true;
        else delete next[key];
        return { pending: next };
      });
    set({ messages: history, input: "", attachments: [] });

    let id = chatId;
    setPending(id || "new", true);
    if (id) {
      save(id, history);
    } else {
      try {
        const chat = await api.createChat({ title: titleFrom(content), messages: forSaving(history) });
        id = chat.chat_id;
        const shown = get().view === view;
        set((s) => ({
          chats: [summary(chat), ...s.chats],
          chatId: shown ? id : s.chatId,
          pending: { ...Object.fromEntries(Object.entries(s.pending).filter(([k]) => k !== "new")), [id]: true },
        }));
        if (shown) onCreated?.(id);
      } catch (e) {
        useStore.getState().setToast(`This chat isn't being saved: ${e.message}`);
      }
    }
    // Still the conversation on screen? The operator may have opened another.
    const shown = () => (id ? get().chatId === id : get().view === view);

    let reply;
    try {
      const body = history
        .map((m, i) => (i === history.length - 1 ? { role: m.role, content, images: m.images } : forModel(m)))
        .filter((m) => m.content || m.images?.length)
        .slice(-MAX_TURNS);
      const res = await api.chat(body);
      reply = {
        imageText: res.image_text || "",
        message: {
          role: "assistant",
          content: res.reply,
          proposal: res.lead_proposal,
          warnings: res.warnings || [],
          draft: res.draft,
          records: res.records || [],
          change: res.change,
          cv: res.cv,
          video: res.video,
        },
      };
    } catch (e) {
      reply = { imageText: "", message: { role: "assistant", content: `Error: ${e.message}` } };
    }

    // Build on what is on screen now: a card may have been acted on meanwhile.
    const current = shown() && get().messages.length === history.length ? get().messages : history;
    const last = history.length - 1;
    const done = [
      ...current.map((m, i) => (i === last && reply.imageText ? { ...m, imageText: reply.imageText } : m)),
      reply.message,
    ];
    if (shown()) set({ messages: done });
    setPending(id || "new", false);
    if (id) {
      await save(id, done);
      get().loadChats(); // the chat just spoken in moves to the top
    }
  },

  rename: async (id, title) => {
    const clean = title.trim();
    const before = get().chats;
    if (!clean || clean === before.find((c) => c.chat_id === id)?.title) return;
    set({ chats: before.map((c) => (c.chat_id === id ? { ...c, title: clean } : c)) });
    try {
      await api.updateChat(id, { title: clean });
    } catch (e) {
      set({ chats: before });
      useStore.getState().setToast(`Couldn't rename: ${e.message}`);
    }
  },

  star: async (id, starred) => {
    const before = get().chats;
    set({ chats: before.map((c) => (c.chat_id === id ? { ...c, starred } : c)) });
    try {
      await api.updateChat(id, { starred });
    } catch (e) {
      set({ chats: before });
      useStore.getState().setToast(`Couldn't ${starred ? "star" : "unstar"}: ${e.message}`);
    }
  },

  // Resolves true when the chat is gone.
  remove: async (id) => {
    try {
      await api.deleteChat(id);
    } catch (e) {
      if (e.status !== 404) {
        useStore.getState().setToast(`Couldn't delete: ${e.message}`);
        return false;
      }
    }
    set((s) => ({ chats: s.chats.filter((c) => c.chat_id !== id) }));
    if (get().chatId === id) get().startNew();
    return true;
  },
}));
