# ============================================================================
# ui/assistant_view.py
# ----------------------------------------------------------------------------
# AI ASSISTANT SCREEN — chat with the library in plain English.
#
# Ask questions like "who has my Harry Potter books?", "what's overdue?", or
# "suggest something like Panipat". AssistantService (Claude API + tool use)
# does the work; this screen is just the chat UI.
#
# The API call runs on a BACKGROUND THREAD so the window never freezes while
# waiting for a reply; the result is delivered back to the UI thread via
# self.after(). Presentation only — no business logic here.
# ============================================================================

import threading
import tkinter as tk
from tkinter import ttk

from services.assistant_service import AssistantService
from ui import theme


class AssistantView(ttk.Frame):
    """A simple chat interface backed by the Claude-powered AssistantService."""

    HEADER_BG = theme.HEADER_BG
    HEADER_FG = theme.HEADER_FG

    def __init__(self, parent, service=None):
        super().__init__(parent, padding=0)
        self.service = service or AssistantService()
        self._history = None       # conversation state for follow-up questions
        self._busy = False
        self._build_ui()
        self._greet()

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=self.HEADER_BG, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(
            header, text="  AI Assistant", bg=self.HEADER_BG, fg=self.HEADER_FG,
            font=("Segoe UI", 16, "bold"),
        ).place(relx=0.0, rely=0.5, anchor="w", x=15)

        # Conversation transcript (read-only Text with colour tags).
        wrap = ttk.Frame(self, padding=(15, 10))
        wrap.grid(row=1, column=0, sticky="nsew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        self.txt = tk.Text(wrap, wrap="word", font=("Segoe UI", 11), state="disabled",
                           background="#ffffff", relief="flat", padx=8, pady=8)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=vsb.set)
        self.txt.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.txt.tag_configure("you", foreground="#1f5c8b", font=("Segoe UI", 11, "bold"))
        self.txt.tag_configure("bot", foreground="#1e8449", font=("Segoe UI", 11, "bold"))
        self.txt.tag_configure("msg", foreground="#2c3e50")
        self.txt.tag_configure("note", foreground="#c0392b")

        # Input row.
        bar = ttk.Frame(self, padding=(15, 0, 15, 12))
        bar.grid(row=2, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)
        self.var_input = tk.StringVar()
        self.entry = ttk.Entry(bar, textvariable=self.var_input, font=("Segoe UI", 11))
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<Return>", lambda e: self._on_send())
        self.btn_send = ttk.Button(bar, text="Send", command=self._on_send)
        self.btn_send.grid(row=0, column=1, padx=(8, 0))

        self.lbl_status = ttk.Label(self, text="", padding=(15, 2), foreground="#888")
        self.lbl_status.grid(row=3, column=0, sticky="w")

    # ------------------------------------------------------------------ #
    # Conversation helpers
    # ------------------------------------------------------------------ #
    def _greet(self):
        ok, why = self.service.availability()
        self._append("Assistant",
                     "Hi! Ask me about your library — e.g. “what's overdue?”, "
                     "“who has my Harry Potter books?”, or “suggest something like Panipat”.")
        if not ok:
            self._append(None, why, note=True)
            self.entry.configure(state="disabled")
            self.btn_send.configure(state="disabled")

    def _append(self, speaker, text, note=False):
        self.txt.configure(state="normal")
        if speaker:
            tag = "you" if speaker == "You" else "bot"
            self.txt.insert("end", f"{speaker}: ", tag)
        self.txt.insert("end", text + "\n\n", "note" if note else "msg")
        self.txt.configure(state="disabled")
        self.txt.see("end")

    # ------------------------------------------------------------------ #
    # Send / receive (background thread so the UI never freezes)
    # ------------------------------------------------------------------ #
    def _on_send(self):
        if self._busy:
            return
        question = self.var_input.get().strip()
        if not question:
            return
        self.var_input.set("")
        self._append("You", question)
        self._set_busy(True)
        threading.Thread(target=self._ask_worker, args=(question,), daemon=True).start()

    def _ask_worker(self, question):
        # Runs off the UI thread. Marshal the result back with self.after().
        result = self.service.ask(question, self._history)
        self.after(0, lambda: self._handle_result(result))

    def _handle_result(self, result):
        self._set_busy(False)
        if result["success"]:
            self._history = result["data"]["history"]
            self._append("Assistant", result["data"]["answer"])
        else:
            self._append(None, "⚠️ " + result["message"], note=True)

    def _set_busy(self, busy):
        self._busy = busy
        self.lbl_status.config(text="Thinking…" if busy else "")
        state = "disabled" if busy else "normal"
        self.btn_send.configure(state=state)
        self.entry.configure(state=state)
        if not busy:
            self.entry.focus_set()


# ----------------------------------------------------------------------------
# Standalone preview:  python -m ui.assistant_view
# (Needs the anthropic package + ANTHROPIC_API_KEY to actually chat.)
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("AI Assistant — Preview")
    root.geometry("760x560")
    view = AssistantView(root)
    view.pack(fill="both", expand=True)
    root.mainloop()
