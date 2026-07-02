# ============================================================================
# ui/borrower_view.py
# ----------------------------------------------------------------------------
# BORROWER MANAGEMENT SCREEN — add, edit, remove and search borrowers.
#
# Shows all borrowers in a professional ttk.Treeview with:
#   - Search box (Name / Phone / Email)
#   - Add    -> opens a blank form dialog (BorrowerService.add_borrower)
#   - Update -> opens a pre-filled dialog; double-click a row does the same
#   - Delete -> soft delete via BorrowerService (guarded server-side)
#   - Refresh
#   - Sortable columns (click a header; click again to reverse)
#   - Responsive layout (table grows/shrinks with the window)
#
# The hidden BorrowerID is stored as each row's internal id (iid), so actions
# target the right person without ever showing the id.
#
# Presentation only: all data work goes through BorrowerService; all field
# validation goes through the Borrower model.
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox

from models.borrower import Borrower
from services.borrower_service import BorrowerService
from ui import theme


class BorrowerListView(ttk.Frame):
    """A framed, sortable list of borrowers with add/edit/delete actions."""

    # Shared palette (see ui/theme.py).
    HEADER_BG = theme.HEADER_BG
    HEADER_FG = theme.HEADER_FG
    ROW_ODD = theme.ROW_ODD
    ROW_EVEN = theme.ROW_EVEN

    # (column id, heading text, width, stretch?)
    COLUMNS = (
        ("name", "Name", 200, True),
        ("phone", "Phone", 150, False),
        ("email", "Email", 220, True),
        ("address", "Address", 240, True),
    )

    def __init__(self, parent, service=None):
        super().__init__(parent, padding=0)
        self.service = service or BorrowerService()
        self._borrowers_by_id = {}
        self._sort_desc = {}

        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ---- Header bar ----------------------------------------------------
        header = tk.Frame(self, bg=self.HEADER_BG, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(
            header, text="  Borrower Management", bg=self.HEADER_BG, fg=self.HEADER_FG,
            font=("Segoe UI", 16, "bold"),
        ).place(relx=0.0, rely=0.5, anchor="w", x=15)

        # ---- Toolbar (search + actions) -----------------------------------
        toolbar = ttk.Frame(self, padding=(15, 12))
        toolbar.grid(row=1, column=0, sticky="ew")
        toolbar.columnconfigure(1, weight=1)

        ttk.Label(toolbar, text="Search:").grid(row=0, column=0, padx=(0, 6))
        self.var_search = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.var_search, width=30)
        search_entry.grid(row=0, column=1, sticky="w")
        search_entry.bind("<Return>", lambda e: self._on_search())

        ttk.Button(toolbar, text="Search", command=self._on_search).grid(row=0, column=2, padx=4)
        ttk.Button(toolbar, text="Refresh", command=self._on_refresh).grid(row=0, column=3, padx=4)
        ttk.Button(toolbar, text="Add", command=self._on_add).grid(row=0, column=4, padx=4)
        ttk.Button(toolbar, text="Update", command=self._on_update).grid(row=0, column=5, padx=4)
        ttk.Button(toolbar, text="Delete", command=self._on_delete).grid(row=0, column=6, padx=4)

        # ---- Treeview + scrollbars ----------------------------------------
        table_wrap = ttk.Frame(self, padding=(15, 0, 15, 10))
        table_wrap.grid(row=2, column=0, sticky="nsew")
        table_wrap.rowconfigure(0, weight=1)
        table_wrap.columnconfigure(0, weight=1)

        self._apply_style()

        col_ids = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(
            table_wrap, columns=col_ids, show="headings", selectmode="browse"
        )
        for col_id, heading, width, stretch in self.COLUMNS:
            self.tree.heading(col_id, text=heading,
                              command=lambda c=col_id: self._sort_by(c))
            self.tree.column(col_id, width=width, stretch=stretch, anchor="w")

        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.tag_configure("odd", background=self.ROW_ODD)
        self.tree.tag_configure("even", background=self.ROW_EVEN)
        self.tree.bind("<Double-1>", self._on_double_click)

        # ---- Status line ---------------------------------------------------
        self.lbl_status = ttk.Label(self, text="", padding=(15, 4), foreground="#555")
        self.lbl_status.grid(row=3, column=0, sticky="w")

    def _apply_style(self):
        """Apply the shared professional Treeview styling (see ui/theme.py)."""
        theme.apply_treeview_style()

    # ------------------------------------------------------------------ #
    # Data loading
    # ------------------------------------------------------------------ #
    def refresh(self):
        """Reload all borrowers and clear any search text."""
        self.var_search.set("")
        self._load(self.service.get_all_borrowers())

    def _load(self, result):
        self.tree.delete(*self.tree.get_children())
        self._borrowers_by_id.clear()

        if not result["success"]:
            self._set_status(result["message"], error=True)
            return

        borrowers = result["data"] or []
        for index, person in enumerate(borrowers):
            self._borrowers_by_id[person.borrower_id] = person
            tag = "even" if index % 2 else "odd"
            self.tree.insert(
                "", "end",
                iid=str(person.borrower_id),
                values=(
                    person.name,
                    person.phone or "",
                    person.email or "",
                    person.address or "",
                ),
                tags=(tag,),
            )
        self._set_status(result["message"])

    # ------------------------------------------------------------------ #
    # Toolbar actions
    # ------------------------------------------------------------------ #
    def _on_search(self):
        keyword = self.var_search.get().strip()
        if not keyword:
            self._load(self.service.get_all_borrowers())
        else:
            self._load(self.service.search_borrower(keyword))

    def _on_refresh(self):
        self.refresh()

    def _on_add(self):
        # Blank form (no borrower) => add mode.
        dialog = _BorrowerFormDialog(self, self.service, borrower=None, on_saved=self.refresh)
        dialog.grab_set()

    def _on_update(self):
        person = self._selected_borrower()
        if person is None:
            messagebox.showwarning("No selection", "Please select a borrower to update.")
            return
        self._open_edit_dialog(person)

    def _on_delete(self):
        person = self._selected_borrower()
        if person is None:
            messagebox.showwarning("No selection", "Please select a borrower to delete.")
            return
        if not messagebox.askyesno("Confirm delete", f"Remove '{person.name}'?"):
            return
        result = self.service.delete_borrower(person.borrower_id)
        if result["success"]:
            messagebox.showinfo("Removed", result["message"])
            self.refresh()
        else:
            messagebox.showerror("Error", result["message"])

    def _on_double_click(self, _event):
        person = self._selected_borrower()
        if person is not None:
            self._open_edit_dialog(person)

    def _open_edit_dialog(self, person):
        dialog = _BorrowerFormDialog(self, self.service, borrower=person, on_saved=self.refresh)
        dialog.grab_set()

    # ------------------------------------------------------------------ #
    # Column sorting
    # ------------------------------------------------------------------ #
    def _sort_by(self, col):
        descending = self._sort_desc.get(col, False)
        rows = [(self.tree.set(iid, col), iid) for iid in self.tree.get_children()]
        rows.sort(key=lambda pair: pair[0].lower(), reverse=descending)
        for position, (_value, iid) in enumerate(rows):
            self.tree.move(iid, "", position)
            self.tree.item(iid, tags=("even" if position % 2 else "odd",))
        self._sort_desc[col] = not descending

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _selected_borrower(self):
        selection = self.tree.selection()
        if not selection:
            return None
        return self._borrowers_by_id.get(int(selection[0]))

    def _set_status(self, message, error=False):
        self.lbl_status.config(text=message, foreground="#c0392b" if error else "#555")


class _BorrowerFormDialog(tk.Toplevel):
    """
    A modal form used for BOTH adding and editing a borrower.
      - borrower is None  -> Add mode  (calls add_borrower)
      - borrower provided -> Edit mode (calls update_borrower)
    """

    def __init__(self, parent, service, borrower=None, on_saved=None):
        super().__init__(parent)
        self.service = service
        self.borrower = borrower
        self.on_saved = on_saved
        self.is_edit = borrower is not None

        self.title("Edit Borrower" if self.is_edit else "Add Borrower")
        self.geometry("440x380")
        self.resizable(False, False)

        self.var_name = tk.StringVar(value=borrower.name if borrower else "")
        self.var_phone = tk.StringVar(value=(borrower.phone if borrower else "") or "")
        self.var_email = tk.StringVar(value=(borrower.email if borrower else "") or "")

        self._build()

    def _build(self):
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        def row(r, text, widget, required=False):
            label = ttk.Frame(frm)
            label.grid(row=r, column=0, sticky="ne" if isinstance(widget, tk.Text) else "e",
                       pady=6, padx=(0, 10))
            ttk.Label(label, text=text).pack(side="left")
            if required:
                tk.Label(label, text=" *", fg="red").pack(side="left")
            widget.grid(row=r, column=1, sticky="ew", pady=6)

        row(0, "Name", ttk.Entry(frm, textvariable=self.var_name), required=True)
        row(1, "Phone", ttk.Entry(frm, textvariable=self.var_phone))
        row(2, "Email", ttk.Entry(frm, textvariable=self.var_email))

        ttk.Label(frm, text="Address").grid(row=3, column=0, sticky="ne", pady=6, padx=(0, 10))
        self.txt_address = tk.Text(frm, height=4, width=28, wrap="word")
        if self.borrower and self.borrower.address:
            self.txt_address.insert("1.0", self.borrower.address)
        self.txt_address.grid(row=3, column=1, sticky="ew", pady=6)

        # Inline status message (validation / errors shown here as well).
        self.lbl_msg = ttk.Label(frm, text="", foreground="#c0392b")
        self.lbl_msg.grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))

        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=5)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")

    def _save(self):
        name = self.var_name.get().strip()
        if not name:
            self.lbl_msg.config(text="Name is required.")
            return

        # Build the Borrower (its constructor validates phone/email format).
        try:
            person = Borrower(
                borrower_id=self.borrower.borrower_id if self.is_edit else None,
                name=name,
                phone=self.var_phone.get().strip() or None,
                email=self.var_email.get().strip() or None,
                address=self.txt_address.get("1.0", "end").strip() or None,
            )
        except ValueError as validation_error:
            self.lbl_msg.config(text=str(validation_error))
            return

        # Persist via the appropriate service call.
        if self.is_edit:
            result = self.service.update_borrower(person)
        else:
            result = self.service.add_borrower(person)

        if result["success"]:
            messagebox.showinfo("Saved", result["message"], parent=self)
            if callable(self.on_saved):
                self.on_saved()
            self.destroy()
        else:
            self.lbl_msg.config(text=result["message"])


# ----------------------------------------------------------------------------
# Standalone preview:  python -m ui.borrower_view
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Borrower Management — Preview")
    root.geometry("880x540")
    view = BorrowerListView(root)
    view.pack(fill="both", expand=True)
    root.mainloop()
