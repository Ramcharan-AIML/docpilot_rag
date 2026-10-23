// The whole app: sidebar of chats + the active conversation + the composer.
// State lives here; components only display it and report clicks.
import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "./api.js";
import Composer from "./components/Composer.jsx";
import { MenuIcon } from "./components/Icons.jsx";
import Message from "./components/Message.jsx";
import Sidebar from "./components/Sidebar.jsx";

const EXAMPLES = [
  "How do I make a FastAPI query parameter optional?",
  "What is chain-of-thought prompting?",
  "How does Docker publish a container port?",
  "What is the difference between MRR and nDCG?",
];

// The theme is a per-browser preference: localStorage can be blocked (private windows),
// so every access is wrapped and the app falls back to light.
function savedTheme() {
  try {
    return localStorage.getItem("docpilot-theme") === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export default function App() {
  const [theme, setTheme] = useState(savedTheme);
  const [chats, setChats] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [files, setFiles] = useState([]);
  const [library, setLibrary] = useState("auto");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const abort = useRef(null);
  const bottom = useRef(null);
  // A chat created a moment ago by the first message is empty on the server: loading it
  // would wipe the message that is streaming in right now. So skip that one load.
  const justCreated = useRef(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme; // CSS switches its colour tokens
    try {
      localStorage.setItem("docpilot-theme", theme);
    } catch {
      /* storage blocked: the theme just is not remembered */
    }
  }, [theme]);

  const refreshChats = useCallback(() => api.listChats().then(setChats).catch((e) => setError(e.message)), []);
  useEffect(() => {
    refreshChats();
  }, [refreshChats]);

  // Open a chat: load its saved messages and files.
  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      setFiles([]);
      return;
    }
    if (justCreated.current === activeId) {
      justCreated.current = null;
      return;
    }
    api
      .getChat(activeId)
      .then((chat) => {
        setMessages(chat.messages);
        setFiles(chat.files);
      })
      .catch((e) => setError(e.message));
  }, [activeId]);

  // While a file is "processing", ask the server every 1.5 s until it is ready or failed.
  useEffect(() => {
    if (!activeId || !files.some((file) => file.status === "processing")) return;
    const timer = setInterval(() => api.listFiles(activeId).then(setFiles).catch(() => {}), 1500);
    return () => clearInterval(timer);
  }, [activeId, files]);

  // Keep the newest words in view while the answer streams in.
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  async function ensureChat() {
    if (activeId) return activeId;
    const chat = await api.createChat();
    justCreated.current = chat.id;
    setActiveId(chat.id);
    setChats((list) => [chat, ...list]);
    return chat.id;
  }

  function newChat() {
    abort.current?.abort();
    setActiveId(null); // the chat is created on the first message or file (no empty chats)
    setLibrary("auto");
    setSidebarOpen(false);
  }

  async function addFiles(list) {
    setError("");
    try {
      const chatId = await ensureChat();
      for (const file of list) {
        try {
          const row = await api.uploadFile(chatId, file); // returns at once: "processing"
          setFiles((current) => [...current, row]);
        } catch (e) {
          setError(`${file.name}: ${e.message}`);
        }
      }
    } catch (e) {
      setError(e.message);
    }
  }

  async function removeFile(file) {
    try {
      await api.deleteFile(activeId, file.id);
      setFiles((current) => current.filter((f) => f.id !== file.id));
    } catch (e) {
      setError(e.message);
    }
  }

  // Patch the last (assistant) message while it streams.
  const updateLast = (change) =>
    setMessages((current) => [...current.slice(0, -1), { ...current.at(-1), ...change(current.at(-1)) }]);

  async function send(question) {
    setError("");
    setBusy(true);
    const controller = new AbortController();
    abort.current = controller;
    setMessages((current) => [
      ...current,
      { role: "user", content: question },
      { role: "assistant", content: "", streaming: true, stage: "Searching your documents" },
    ]);
    try {
      const chatId = await ensureChat();
      await api.streamMessage(
        chatId,
        question,
        library,
        (event) => {
          if (event.type === "sources") updateLast(() => ({ stage: "Writing the answer" }));
          if (event.type === "token") updateLast((last) => ({ content: last.content + event.text }));
          if (event.type === "done")
            updateLast(() => ({
              content: event.answer, // the guarded final text (may replace the streamed draft)
              status: event.status,
              sources: event.sources,
              timings: event.timings,
              streaming: false,
            }));
          if (event.type === "error") updateLast(() => ({ streaming: false, error: event.message }));
        },
        controller.signal,
      );
    } catch (e) {
      const stopped = e.name === "AbortError";
      updateLast((last) => ({ streaming: false, error: stopped ? "Stopped." : e.message, content: last.content }));
    } finally {
      setBusy(false);
      refreshChats(); // new title, new order
    }
  }

  async function removeChat(id) {
    try {
      await api.deleteChat(id);
      if (id === activeId) setActiveId(null);
      refreshChats();
    } catch (e) {
      setError(e.message);
    }
  }

  async function rename(id, title) {
    try {
      await api.renameChat(id, title);
      refreshChats();
    } catch (e) {
      setError(e.message);
    }
  }

  const title = chats.find((chat) => chat.id === activeId)?.title || "New chat";

  return (
    <div
      className="app"
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(event) => {
        if (event.currentTarget === event.target) setDragging(false);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        addFiles([...event.dataTransfer.files]);
      }}
    >
      <Sidebar
        chats={chats}
        activeId={activeId}
        open={sidebarOpen}
        theme={theme}
        onTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
        onNew={newChat}
        onSelect={(id) => {
          setActiveId(id);
          setLibrary("auto");
          setSidebarOpen(false);
        }}
        onRename={rename}
        onDelete={removeChat}
      />
      {sidebarOpen && <div className="scrim" onClick={() => setSidebarOpen(false)} />}

      <main className="main">
        <header className="topbar">
          <button className="icon-button menu" onClick={() => setSidebarOpen(true)} title="Chats">
            <MenuIcon />
          </button>
          <h1>{title}</h1>
        </header>

        <section className="conversation">
          {messages.length === 0 ? (
            <div className="welcome">
              <span className="badge">Cited answers · Guardrails on</span>
              <h2>What do you want to know?</h2>
              <p className="muted">
                Ask about the built-in library (FastAPI, Pydantic, Docker, RAG papers), or drop a PDF / Markdown
                file here to chat with it.
              </p>
              <div className="examples">
                {EXAMPLES.map((example) => (
                  <button key={example} className="example" disabled={busy} onClick={() => send(example)}>
                    {example}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message, index) => (
                <Message key={index} message={message} />
              ))}
              <div ref={bottom} />
            </div>
          )}
        </section>

        {error && (
          <div className="error-bar" onClick={() => setError("")}>
            {error} <span className="muted">(click to close)</span>
          </div>
        )}
        <Composer
          files={files}
          library={library}
          busy={busy}
          onLibrary={setLibrary}
          onSend={send}
          onStop={() => abort.current?.abort()}
          onFiles={addFiles}
          onRemoveFile={removeFile}
        />
      </main>

      {dragging && (
        <div className="drop-overlay">
          <div>Drop PDF, Markdown or text files to add them to this chat</div>
        </div>
      )}
    </div>
  );
}
