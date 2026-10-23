"""Chats (D-061): saved conversations, per-chat files, memory, streaming answers.

store.py   -> SQLite tables: chats, messages, files
jobs.py    -> background indexing of uploaded files
memory.py  -> follow-up questions rewritten with the chat history
service.py -> one chat turn, end to end (guards, memory, retrieval, streaming)
"""
