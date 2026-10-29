"""
Server-side AI Assistant integration for termchat.
Allows any terminal or web user to type /ai <question> or @ai <question>
and get fast answers broadcast in real time.
"""

from termchat.ai import get_ai_config, query_llm

__all__ = ["get_ai_config", "query_llm"]
