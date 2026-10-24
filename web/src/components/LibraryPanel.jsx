// The demo library on the welcome screen (D-066): which documents DocPilot answers from,
// with their licence. The list comes from GET /api/library, i.e. from what the live index
// really holds, so it can never show a document the site does not have.
import { LinkIcon } from "./Icons.jsx";

const SHOWN = 4; // document names per card before "+N more"

function LibraryCard({ item }) {
  const extra = item.documents.length - SHOWN;
  return (
    <article className="library-card">
      <header>
        <h3>{item.title}</h3>
        <span className="kind">{item.kind}</span>
      </header>
      <ul className="doc-list">
        {item.documents.slice(0, SHOWN).map((name) => (
          <li key={name}>{name}</li>
        ))}
        {extra > 0 && <li className="muted">+{extra} more</li>}
      </ul>
      <footer>
        <span>
          {item.documents.length} {item.documents.length === 1 ? "document" : "documents"}
        </span>
        {item.licence_url.startsWith("http") ? (
          <a href={item.licence_url} target="_blank" rel="noreferrer" title={item.licence}>
            {item.licence.split(" (")[0]} <LinkIcon />
          </a>
        ) : (
          <span>{item.licence.split(" (")[0]}</span>
        )}
      </footer>
    </article>
  );
}

export default function LibraryPanel({ items }) {
  if (!items.length) return null;
  return (
    <section className="library-panel" aria-label="Demo library">
      <div className="library-head">
        <h2>Demo library</h2>
        <p className="muted small">
          Open-licence documents DocPilot answers from, with citations. Attach your own file to chat with it instead.
        </p>
      </div>
      <div className="library-grid">
        {items.map((item) => (
          <LibraryCard key={item.key} item={item} />
        ))}
      </div>
    </section>
  );
}
