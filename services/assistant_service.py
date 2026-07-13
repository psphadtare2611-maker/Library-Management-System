# ============================================================================
# services/assistant_service.py
# ----------------------------------------------------------------------------
# AI ASSISTANT SERVICE — a natural-language assistant over the library, powered
# by the Claude API (Anthropic).
#
# HOW IT WORKS (tool use / function calling):
#   1. The user asks a plain-English question ("who has my Harry Potter books?").
#   2. We send the question to Claude along with a set of TOOLS — small typed
#      functions that wrap this app's existing services (search, reports,
#      statistics).
#   3. Claude decides which tool(s) to call; we execute them against the live
#      database and hand the results back.
#   4. Claude reads the results and replies in natural language.
#
# The heavy lifting (deciding what to do) is Claude's; the "hands" are this
# app's own services — so the assistant can only ever read real library data.
#
# SAFETY / ROBUSTNESS:
#   - The Anthropic SDK is imported LAZILY so the whole app still runs if it
#     isn't installed (the screen just shows a friendly message).
#   - The API key is read from the ANTHROPIC_API_KEY environment variable — it
#     is never hardcoded or committed.
#   - Every failure (missing package, missing key, network/API error) becomes a
#     clean {success: False, message} response, never a crash.
# ============================================================================

import os

from config.settings import ASSISTANT_MODEL, ASSISTANT_MAX_TOKENS
from services.service_base import ServiceBase
from services.search_service import SearchService
from services.book_service import BookService
from services.report_service import ReportService
from services.statistics_service import StatisticsService
from utils.logger import logger


SYSTEM_PROMPT = (
    "You are the friendly assistant for a personal home-library desktop app. "
    "Answer the owner's questions about their books, borrowers, and loans using "
    "ONLY the provided tools — never invent titles, people, or numbers. "
    "Be concise and conversational. If a tool returns nothing, say so plainly. "
    "If a question is unrelated to the library, politely say that's outside what "
    "you can help with."
)


class AssistantService(ServiceBase):
    """Natural-language Q&A over the library using Claude tool use."""

    # Tool definitions handed to Claude. Each maps to a method on this service
    # that calls the app's real services.
    TOOLS = [
        {
            "name": "search_library",
            "description": (
                "Search books and borrowers by any keyword — title, author, "
                "category, borrower name, phone, or status. Use for questions "
                "like 'who has X', 'do we have Y', 'find Z'. Issued books show "
                "who currently holds them."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The search keyword."}},
                "required": ["query"],
            },
        },
        {
            "name": "list_available_books",
            "description": "List every book currently available to borrow.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "list_borrowed_books",
            "description": "List books currently on loan, with who has each one and its due date.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "list_overdue_books",
            "description": "List overdue books (past their due date) with borrower and days overdue.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_statistics",
            "description": (
                "Library statistics: total/available/borrowed counts, books "
                "borrowed per person, and the most borrowed author and category."
            ),
            "input_schema": {"type": "object", "properties": {}},
        },
    ]

    def __init__(self, book_service=None, search_service=None, report_service=None,
                 statistics_service=None):
        self.book_service = book_service or BookService()
        self.search_service = search_service or SearchService()
        self.report_service = report_service or ReportService()
        self.statistics_service = statistics_service or StatisticsService()

    # ------------------------------------------------------------------ #
    # Availability check (used by the UI to show a helpful hint)
    # ------------------------------------------------------------------ #
    @staticmethod
    def availability():
        """Return (ok, message) describing whether the assistant can run."""
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False, "The 'anthropic' package isn't installed. Run:  pip install anthropic"
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False, ("No API key found. Set the ANTHROPIC_API_KEY environment "
                           "variable to your Anthropic key, then reopen this screen.")
        return True, "Ready."

    # ------------------------------------------------------------------ #
    # Ask a question (runs the tool-use loop)
    # ------------------------------------------------------------------ #
    def ask(self, question, history=None):
        """
        Answer a natural-language question about the library.

        history : optional prior message list (for follow-up questions).
        Returns data = {"answer": str, "history": list} on success.
        """
        # Fail fast with a precise message if the package or key is missing.
        ok, why = self.availability()
        if not ok:
            return self._response(False, why)

        import anthropic

        messages = list(history or [])
        messages.append({"role": "user", "content": question})

        try:
            client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from the environment

            # Agentic loop: let Claude call tools until it has a final answer.
            for _ in range(6):   # safety cap on tool rounds
                response = client.messages.create(
                    model=ASSISTANT_MODEL,
                    max_tokens=ASSISTANT_MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=self.TOOLS,
                    messages=messages,
                )

                if response.stop_reason == "tool_use":
                    # Record Claude's turn (includes the tool_use blocks)...
                    messages.append({"role": "assistant", "content": response.content})
                    # ...run each requested tool and return all results together.
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            output = self._run_tool(block.name, block.input)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": output,
                            })
                    messages.append({"role": "user", "content": tool_results})
                    continue

                # No more tools — extract the final natural-language answer.
                answer = "".join(b.text for b in response.content if b.type == "text").strip()
                messages.append({"role": "assistant", "content": response.content})
                return self._response(True, "OK", {
                    "answer": answer or "(no answer)",
                    "history": messages,
                })

            return self._response(False, "Sorry — that took too many steps. Please rephrase.")
        except anthropic.AuthenticationError:
            return self._response(False, "Your Anthropic API key was rejected. Check ANTHROPIC_API_KEY.")
        except anthropic.APIError as api_error:
            logger.error(f"assistant API error: {api_error}")
            return self._response(False, "The AI service returned an error. Please try again.")
        except Exception as error:
            logger.error(f"assistant failed: {error}")
            return self._response(False, "The assistant is unavailable right now.")

    # ------------------------------------------------------------------ #
    # Tool execution — the assistant's "hands" (calls the real services)
    # ------------------------------------------------------------------ #
    def _run_tool(self, name, tool_input):
        """Execute the tool Claude requested and return a text result."""
        try:
            if name == "search_library":
                result = self.search_service.universal_search(tool_input.get("query", ""))
                if not result["success"]:
                    return f"Error: {result['message']}"
                items = result["data"]
                if not items:
                    return "No matching books or borrowers."
                return "\n".join(
                    f"[{it['type']}] {it['name']} — {it['details'] or ''} ({it['status']})"
                    for it in items
                )

            if name == "list_available_books":
                return self._format_report(self.report_service.available_books())

            if name == "list_borrowed_books":
                return self._format_report(self.report_service.borrowed_books())

            if name == "list_overdue_books":
                return self._format_report(self.report_service.overdue_books())

            if name == "get_statistics":
                return self._format_stats(self.statistics_service.get_statistics())

            return f"Error: unknown tool '{name}'."
        except Exception as error:
            logger.error(f"tool '{name}' failed: {error}")
            return f"Error running '{name}'."

    # ------------------------------------------------------------------ #
    # Formatting helpers (turn service results into compact text for Claude)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _format_report(result):
        if not result["success"]:
            return f"Error: {result['message']}"
        data = result["data"]
        rows = data["rows"]
        if not rows:
            return "(none)"
        headings = [heading for heading, _width in data["columns"]]
        lines = [" | ".join(headings)]
        for row in rows[:50]:
            lines.append(" | ".join("" if v is None else str(v) for v in row))
        return "\n".join(lines)

    @staticmethod
    def _format_stats(result):
        if not result["success"]:
            return f"Error: {result['message']}"
        d = result["data"]
        parts = [
            f"Total books: {d['total_books']}",
            f"Available: {d['available_books']}",
            f"Borrowed: {d['borrowed_books']}",
            f"Borrowers: {d['total_borrowers']}",
        ]
        if d["top_author"]:
            parts.append(f"Most borrowed author: {d['top_author']['author']} ({d['top_author']['count']})")
        if d["top_category"]:
            parts.append(f"Most borrowed category: {d['top_category']['category']} ({d['top_category']['count']})")
        if d["per_person"]:
            per = ", ".join(f"{p['name']}: {p['count']}" for p in d["per_person"])
            parts.append(f"Books borrowed per person — {per}")
        return "\n".join(parts)
