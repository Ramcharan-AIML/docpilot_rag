// Every call to the DocPilot API lives here, so components never build URLs themselves.
// The UI has no RAG logic: guards, memory and retrieval all run on the server.

const BASE = "/api";

// Private chats (A1, D-063): this browser's random visitor id, made once and kept in
// localStorage. The server shows a visitor only the chats made with their id.
// Like a cloakroom ticket: no password, so it is privacy, not security.
const VISITOR_KEY = "docpilot-visitor-id";
let memoryId = null; // fallback when localStorage is blocked (private window, strict settings)

// randomUUID exists only on HTTPS and localhost; plain http://<server-ip> (first boot,
// before HTTPS) still has getRandomValues: 16 random bytes as 32 hex characters.
function newId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function visitorId() {
  try {
    let id = localStorage.getItem(VISITOR_KEY);
    if (!id) {
      id = newId();
      localStorage.setItem(VISITOR_KEY, id);
    }
    return id;
  } catch {
    memoryId = memoryId || newId(); // chats last until the tab is closed
    return memoryId;
  }
}

// Every call goes through here, so no request can forget the header.
function call(path, options = {}) {
  const headers = { ...options.headers, "X-Visitor-Id": visitorId() };
  return fetch(`${BASE}${path}`, { ...options, headers });
}

// FastAPI puts the reason for an error in {"detail": "..."}: show that, not "Error 400".
async function parse(response) {
  if (!response.ok) {
    let detail = "";
    try {
      detail = (await response.json()).detail;
    } catch {
      /* body was not JSON */
    }
    throw new Error(typeof detail === "string" && detail ? detail : `Server error ${response.status}`);
  }
  return response.json();
}

export const getLibrary = () => call("/library").then(parse); // the demo library panel (D-066)
export const listChats = () => call("/chats").then(parse);
export const createChat = () => call("/chats", { method: "POST" }).then(parse);
export const getChat = (id) => call(`/chats/${id}`).then(parse);
export const listFiles = (id) => call(`/chats/${id}/files`).then(parse);
export const deleteChat = (id) => call(`/chats/${id}`, { method: "DELETE" }).then(parse);
export const deleteFile = (id, fileId) =>
  call(`/chats/${id}/files/${fileId}`, { method: "DELETE" }).then(parse);

export const renameChat = (id, title) =>
  call(`/chats/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  }).then(parse);

export function uploadFile(id, file) {
  const form = new FormData();
  form.append("file", file);
  // Returns at once with status "processing": indexing runs in the background (D-061).
  return call(`/chats/${id}/files`, { method: "POST", body: form }).then(parse);
}

// Ask a question; the answer arrives as Server-Sent Events: "data: {json}\n\n" blocks.
// onEvent gets each event: sources, token (many), then done (or error).
export async function streamMessage(id, question, library, onEvent, signal) {
  const response = await call(`/chats/${id}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, library }), // "main" | "off" | "files" (D-066)
    signal, // lets the Stop button cancel the request
  });
  if (!response.ok) await parse(response); // throws with the server's message

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // A network packet can end in the middle of an event: only handle complete ones.
    let end;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      if (block.startsWith("data: ")) onEvent(JSON.parse(block.slice(6)));
    }
  }
}
