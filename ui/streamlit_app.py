"""DocPilot web UI (D-060). Streamlit re-runs this whole file, top to bottom, on every click.

Run (two terminals):
    uvicorn docpilot.api:app            # the API, port 8000
    streamlit run ui/streamlit_app.py   # this UI, opens http://localhost:8501

The UI holds no RAG logic: it sends questions and files to the API and shows the result,
so the guardrails and the measured pipeline apply to everything typed here.
"""

import streamlit as st
from api_client import (  # same folder: Streamlit puts this file's folder on the path
    API_URL,
    ApiError,
    ask,
    is_api_up,
    list_uploads,
    source_rows,
    status_note,
    timing_rows,
    upload,
)

st.set_page_config(page_title="DocPilot", page_icon="📘", layout="wide")

# st.session_state survives the re-runs; a normal variable would reset on every click.
if "history" not in st.session_state:
    st.session_state.history = []  # [{"question", "library", "result"}], oldest first


def show_result(result: dict) -> None:
    """Answer, a note if it was refused, then sources and time per stage."""
    st.markdown(result["answer"])
    note = status_note(result["status"])
    if note:
        st.caption(f"ℹ️ {note}")
    if result["sources"]:
        with st.expander(f"Sources ({len(result['sources'])})"):
            st.dataframe(source_rows(result["sources"]), hide_index=True)
    with st.expander(f"Time: {result['timings_ms'].get('total', 0):.0f} ms"):
        st.dataframe(timing_rows(result["timings_ms"]), hide_index=True)


# ---------- sidebar: API status, library choice, uploads ----------
with st.sidebar:
    st.header("DocPilot")
    if is_api_up():
        st.success(f"API connected ({API_URL})")
    else:
        st.error(f"API not reachable at {API_URL}. Start: uvicorn docpilot.api:app")

    library = st.radio(
        "Search in",
        options=["main", "uploads"],
        format_func=lambda name: {"main": "Main library (20 docs)", "uploads": "My uploads"}[name],
        help="Main library = the measured, evaluated documents. My uploads = your own PDFs.",
    )

    st.subheader("Add a PDF to My uploads")
    pdf = st.file_uploader("PDF, up to 30 pages", type=["pdf"])
    if pdf is not None and st.button("Upload and index", type="primary"):
        # Docling reads about 4 s per page on this laptop, so tell the user to wait.
        with st.spinner(f"Reading {pdf.name} (about 4 s per page)..."):
            try:
                done = upload(pdf.name, pdf.getvalue())
                st.success(
                    f"{done['source']}: {done['pages']} pages, {done['chunks']} chunks, "
                    f"{sum(done['seconds'].values()):.0f} s"
                )
            except ApiError as error:
                st.error(str(error))

    try:
        documents = list_uploads()
    except ApiError:
        documents = {}
    if documents:
        st.caption("In My uploads:")
        for source, chunks in documents.items():
            st.caption(f"• {source.removeprefix('uploads/')} ({chunks} chunks)")

# ---------- main area: the conversation ----------
st.title("📘 DocPilot")
st.caption(
    "Answers only from the documents, with citations like [1]. "
    "If the answer is not there, it says so."
)

for turn in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(turn["question"])
        st.caption("My uploads" if turn["library"] == "uploads" else "Main library")
    with st.chat_message("assistant"):
        show_result(turn["result"])

question = st.chat_input("Ask a question about the documents")
if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Searching and answering..."):
            try:
                result = ask(question, library)
            except ApiError as error:
                st.error(str(error))
                result = None
        if result is not None:
            show_result(result)
            st.session_state.history.append(
                {"question": question, "library": library, "result": result}
            )
