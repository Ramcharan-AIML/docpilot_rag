// One message bubble. Assistant answers are Markdown (lists, tables, code blocks), and
// citations like [1] become small numbered badges that match the source cards below.
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { LogoIcon } from "./Icons.jsx";

const STATUS_NOTES = {
  not_found: "Not in the documents, so DocPilot did not guess.",
  blocked_input: "Blocked by the input guard: this looked like an attempt to change DocPilot's rules.",
  blocked_output: "The draft answer had no valid citation, so it was withheld.",
  chat: "Answered from this conversation, not from the documents.",
};

const STAGE_NAMES = {
  input_guard: "Input guard",
  condense: "Memory (rewrite follow-up)",
  embed_query: "Embed question",
  search: "Hybrid search",
  rerank: "Rerank",
  first_token: "First word of the answer",
  llm: "LLM answer (complete)",
  output_guard: "Output guard",
  total: "Total",
};

// The model writes citations as [1], [1, 2], 【1】 or 【1†L1-L4】. Turn them into links to
// "#cite-1" (rendered as badges), but never inside code: `items[0]` is code, not a citation.
export function linkCitations(text) {
  return text
    .split(/(```[\s\S]*?```|`[^`\n]*`)/g) // odd parts are code
    .map((part, index) => {
      if (index % 2 === 1) return part;
      return part
        .replace(/【(\d+)(?:†[^】]*)?】/g, "[$1]")
        .replace(/\[(\d+(?:\s*,\s*\d+)*)\](?!\()/g, (_, numbers) =>
          numbers
            .split(",")
            .map((n) => `[${n.trim()}](#cite-${n.trim()})`)
            .join(""),
        );
    })
    .join("");
}

function Citation({ href, children }) {
  if (href?.startsWith("#cite-")) {
    return <span className="cite">{children}</span>;
  }
  return (
    <a href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  );
}

function Sources({ sources }) {
  return (
    <div className="sources">
      {sources.map((source, index) => (
        <div className="source-card" key={`${source.source}-${source.chunk_number}`} title={source.source}>
          <span className="cite">{index + 1}</span>
          <span className="source-name">{source.name}</span>
          {source.section && <span className="source-section">{source.section}</span>}
        </div>
      ))}
    </div>
  );
}

function Timings({ timings }) {
  const [open, setOpen] = useState(false);
  const total = timings.total;
  if (!total) return null;
  return (
    <div className="timings">
      <button className="link-button" onClick={() => setOpen(!open)}>
        {(total / 1000).toFixed(1)} s
        {timings.first_token ? ` · first words after ${(timings.first_token / 1000).toFixed(1)} s` : ""}
        {open ? " ▾" : " ▸"}
      </button>
      {open && (
        <table>
          <tbody>
            {Object.entries(timings).map(([stage, ms]) => (
              <tr key={stage}>
                <td>{STAGE_NAMES[stage] || stage}</td>
                <td className="num">{ms < 1 ? "<1" : Math.round(ms)} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function Message({ message }) {
  if (message.role === "user") {
    return (
      <div className="message user">
        <div className="bubble">{message.content}</div>
      </div>
    );
  }
  const note = STATUS_NOTES[message.status];
  const blocked = message.status?.startsWith("blocked");
  return (
    <div className="message assistant">
      <div className="avatar">
        <LogoIcon />
      </div>
      <div className="answer">
        {message.content ? (
          <div className={`markdown ${message.streaming ? "streaming" : ""}`}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ a: Citation }}>
              {linkCitations(message.content)}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="thinking">
            <span /> <span /> <span />
            <em>{message.stage || "Searching your documents"}</em>
          </div>
        )}
        {note && !message.streaming && <p className={`note ${blocked ? "warn" : ""}`}>{note}</p>}
        {message.error && <p className="note warn">{message.error}</p>}
        {!message.streaming && message.sources?.length > 0 && <Sources sources={message.sources} />}
        {!message.streaming && message.timings && <Timings timings={message.timings} />}
      </div>
    </div>
  );
}
