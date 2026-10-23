// Every call to the DocPilot API lives here, so components never build URLs themselves.
// The UI has no RAG logic: guards, memory and retrieval all run on the server.

const BASE = "/api";

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

export const listChats = () => fetch(`${BASE}/chats`).then(parse);
export const createChat = () => fetch(`${BASE}/chats`, { method: "POST" }).then(parse);
export const getChat = (id) => fetch(`${BASE}/chats/${id}`).then(parse);
export const listFiles = (id) => fetch(`${BASE}/chats/${id}/files`).then(parse);
export const deleteChat = (id) => fetch(`${BASE}/chats/${id}`, { method: "DELETE" }).then(parse);
export const deleteFile = (id, fileId) =>
  fetch(`${BASE}/chats/${id}/files/${fileId}`, { method: "DELETE" }).then(parse);

export const renameChat = (id, title) =>
  fetch(`${BASE}/chats/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  }).then(parse);

export function uploadFile(id, file) {
  const form = new FormData();
  form.append("file", file);
  // Returns at once with status "processing": indexing runs in the background (D-061).
  return fetch(`${BASE}/chats/${id}/files`, { method: "POST", body: form }).then(parse);
}

// Ask a question; the answer arrives as Server-Sent Events: "data: {json}\n\n" blocks.
// onEvent gets each event: sources, token (many), then done (or error).
export async function streamMessage(id, question, library, onEvent, signal) {
  const response = await fetch(`${BASE}/chats/${id}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, library: library === "auto" ? null : library }),
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
