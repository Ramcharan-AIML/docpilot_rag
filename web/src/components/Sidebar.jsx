// Left panel, like ChatGPT: New chat, then every saved chat (newest activity first).
// A chat can be renamed (pencil) or deleted (bin, with a confirmation).
import { useState } from "react";
import { ChatIcon, LogoIcon, MoonIcon, PencilIcon, PlusIcon, SunIcon, TrashIcon } from "./Icons.jsx";

function ChatRow({ chat, active, onSelect, onRename, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(chat.title);

  function save() {
    setEditing(false);
    const clean = title.trim();
    if (clean && clean !== chat.title) onRename(chat.id, clean);
    else setTitle(chat.title);
  }

  if (editing) {
    return (
      <div className="chat-row active">
        <input
          className="rename-input"
          value={title}
          autoFocus
          maxLength={60}
          onChange={(event) => setTitle(event.target.value)}
          onBlur={save}
          onKeyDown={(event) => {
            if (event.key === "Enter") save();
            if (event.key === "Escape") {
              setTitle(chat.title);
              setEditing(false);
            }
          }}
        />
      </div>
    );
  }
  return (
    <div className={`chat-row ${active ? "active" : ""}`} onClick={() => onSelect(chat.id)}>
      <ChatIcon />
      <span className="chat-title" title={chat.title}>{chat.title}</span>
      <span className="row-actions">
        <button
          className="icon-button"
          title="Rename"
          onClick={(event) => {
            event.stopPropagation(); // do not also select the chat
            setTitle(chat.title);
            setEditing(true);
          }}
        >
          <PencilIcon />
        </button>
        <button
          className="icon-button danger"
          title="Delete chat"
          onClick={(event) => {
            event.stopPropagation();
            if (window.confirm(`Delete "${chat.title}" and its files?`)) onDelete(chat.id);
          }}
        >
          <TrashIcon />
        </button>
      </span>
    </div>
  );
}

export default function Sidebar({ chats, activeId, open, theme, onTheme, onNew, onSelect, onRename, onDelete }) {
  return (
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <div className="brand">
        <LogoIcon />
        <span>DocPilot</span>
      </div>
      <button className="new-chat" onClick={onNew}>
        <PlusIcon /> New chat
      </button>
      <div className="chat-list">
        {chats.length === 0 && <p className="muted small pad">No chats yet.</p>}
        {chats.map((chat) => (
          <ChatRow
            key={chat.id}
            chat={chat}
            active={chat.id === activeId}
            onSelect={onSelect}
            onRename={onRename}
            onDelete={onDelete}
          />
        ))}
      </div>
      <button className="theme-toggle" onClick={onTheme}>
        {theme === "dark" ? <SunIcon /> : <MoonIcon />}
        {theme === "dark" ? "Light mode" : "Dark mode"}
      </button>
      <p className="sidebar-foot muted small">
        Answers come only from documents, with citations. Guardrails on.
      </p>
    </aside>
  );
}
