"""Phase 6 guardrails (D-059): plain-Python checks around the RAG pipeline.

input_guard   -> runs before retrieval and the LLM (empty, too long, prompt injection)
context_guard -> wraps retrieved chunks as untrusted data (indirect injection)
output_guard  -> runs on the LLM answer (cite or refuse, prompt leak, secrets)
"""
