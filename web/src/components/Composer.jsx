// The input area at the bottom: file chips, attach button, "search in" switch, text box,
// Send / Stop. Enter sends, Shift+Enter makes a new line (like ChatGPT).
import { useEffect, useRef, useState } from "react";
import { AlertIcon, CheckIcon, ClipIcon, CloseIcon, FileIcon, SendIcon, StopIcon } from "./Icons.jsx";

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

export default function Composer({ files, library, busy, onLibrary, onSend, onStop, onFiles, onRemoveFile }) {
  const [text, setText] = useState("");
  const box = useRef(null);
  const picker = useRef(null);
  const hasReady = files.some((file) => file.status === "ready");

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
          placeholder={hasReady ? "Ask about your files…" : "Ask DocPilot, or attach a PDF / Markdown file…"}
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
          <select
            className="library-select"
            value={library}
            onChange={(event) => onLibrary(event.target.value)}
            title="Where DocPilot searches"
          >
            <option value="auto">Auto: {hasReady ? "this chat's files" : "main library"}</option>
            <option value="files" disabled={!hasReady}>This chat's files</option>
            <option value="main">Main library (20 docs)</option>
          </select>
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
