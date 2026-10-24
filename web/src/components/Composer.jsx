// The input area at the bottom: file chips, attach button, demo-library switch, text box,
// Send / Stop. Enter sends, Shift+Enter makes a new line (like ChatGPT).
import { useEffect, useRef, useState } from "react";
import {
  AlertIcon,
  BookIcon,
  CheckIcon,
  ClipIcon,
  CloseIcon,
  FileIcon,
  LockIcon,
  SendIcon,
  StopIcon,
} from "./Icons.jsx";

// D-066: ON = answer from the demo library. Once the chat has a file it is LOCKED to that
// chat's files (no mixing of a personal file with the demo docs); a new chat unlocks it.
function LibrarySwitch({ on, locked, onToggle }) {
  if (locked) {
    return (
      <span className="library-switch locked" title="This chat answers only from its files. Start a new chat to use the demo library.">
        <LockIcon /> Your files only
      </span>
    );
  }
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      className={`library-switch ${on ? "on" : ""}`}
      title={on ? "Answers come from the demo library" : "Demo library off: attach a file to ask about it"}
      onClick={onToggle}
    >
      <BookIcon /> Demo library <span className="switch-track"><span className="switch-dot" /></span>
    </button>
  );
}

export const ACCEPT = ".pdf,.md,.txt";

function FileChip({ file, onRemove }) {
  const status = {
    processing: <span className="spinner" title="Indexing in the background..." />,
    ready: <span className="ok"><CheckIcon /></span>,
    failed: <span className="bad" title={file.error}><AlertIcon /></span>,
  }[file.status];
  const detail =
    file.status === "ready"
      ? `${file.pages} ${file.pages === 1 ? "page" : "pages"}`
      : file.status === "failed"
        ? file.error
        : "Indexing…";
  return (
    <div className={`file-chip ${file.status}`} title={file.error || file.name}>
      <FileIcon />
      <div className="file-text">
        <span className="file-name">{file.name}</span>
        <span className="file-detail">{detail}</span>
      </div>
      {status}
      {onRemove && (
        <button className="chip-close" title="Remove file" onClick={() => onRemove(file)}>
          <CloseIcon />
        </button>
      )}
    </div>
  );
}

export default function Composer({ files, libraryOn, locked, busy, onToggleLibrary, onSend, onStop, onFiles, onRemoveFile }) {
  const [text, setText] = useState("");
  const box = useRef(null);
  const picker = useRef(null);
  const placeholder = locked
    ? "Ask about your files…"
    : libraryOn
      ? "Ask about FastAPI, Pydantic, Docker, RAG… or attach a file"
      : "Attach a PDF, Markdown or text file to ask about it…";

  // Grow the text box with its content, up to a limit (then it scrolls).
  useEffect(() => {
    const element = box.current;
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 200)}px`;
  }, [text]);

  function send() {
    const question = text.trim();
    if (!question || busy) return;
    onSend(question);
    setText("");
  }

  return (
    <div className="composer-wrap">
      <div className="composer">
        {files.length > 0 && (
          <div className="file-row">
            {files.map((file) => (
              <FileChip key={file.id} file={file} onRemove={onRemoveFile} />
            ))}
          </div>
        )}
        <textarea
          ref={box}
          rows={1}
          value={text}
          placeholder={placeholder}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              send();
            }
          }}
        />
        <div className="composer-bar">
          <button className="icon-button" title="Attach files (PDF, .md, .txt)" onClick={() => picker.current.click()}>
            <ClipIcon />
          </button>
          <input
            ref={picker}
            type="file"
            accept={ACCEPT}
            multiple
            hidden
            onChange={(event) => {
              onFiles([...event.target.files]);
              event.target.value = ""; // so the same file can be picked again
            }}
          />
          <LibrarySwitch on={libraryOn} locked={locked} onToggle={onToggleLibrary} />
          <span className="grow" />
          {busy ? (
            <button className="send stop" title="Stop" onClick={onStop}>
              <StopIcon />
            </button>
          ) : (
            <button className="send" title="Send (Enter)" disabled={!text.trim()} onClick={send}>
              <SendIcon />
            </button>
          )}
        </div>
      </div>
      <p className="disclaimer">DocPilot answers only from documents and cites them. Check important facts.</p>
    </div>
  );
}
