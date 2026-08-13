"""Tkinter desktop interface for preview-first file organization."""

from __future__ import annotations

import tkinter as tk
from contextlib import suppress
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .config import ConfigError
from .core import PilotError
from .desktop import DesktopSession, default_data_dir
from .models import Operation, Status


class PilotWindow:
    """Small native interface backed entirely by the tested core."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.session = DesktopSession()
        self.target = tk.StringVar()
        self.config = tk.StringVar()
        self.status = tk.StringVar(
            value="Choose a folder, then preview. Nothing moves automatically."
        )
        self._build()
        self._sync_actions()

    def _build(self) -> None:
        self.root.title("Carrot File Pilot")
        self.root.geometry("940x620")
        self.root.minsize(720, 480)

        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)
        ttk.Label(outer, text="Carrot File Pilot", font=("", 20, "bold")).pack(anchor=tk.W)
        ttk.Label(
            outer,
            text="Preview every move before organizing. Existing files are never overwritten.",
        ).pack(anchor=tk.W, pady=(2, 16))

        fields = ttk.Frame(outer)
        fields.pack(fill=tk.X)
        ttk.Label(fields, text="Folder").grid(row=0, column=0, sticky=tk.W, pady=4)
        target_entry = ttk.Entry(fields, textvariable=self.target)
        target_entry.grid(row=0, column=1, sticky=tk.EW, padx=8, pady=4)
        target_entry.bind("<KeyRelease>", self._input_changed)
        ttk.Button(fields, text="Browse…", command=self._choose_target).grid(row=0, column=2)

        ttk.Label(fields, text="Rules").grid(row=1, column=0, sticky=tk.W, pady=4)
        config_entry = ttk.Entry(fields, textvariable=self.config)
        config_entry.grid(row=1, column=1, sticky=tk.EW, padx=8, pady=4)
        config_entry.bind("<KeyRelease>", self._input_changed)
        ttk.Button(fields, text="Custom JSON…", command=self._choose_config).grid(row=1, column=2)
        ttk.Label(fields, text="Leave blank to use the safe built-in categories.").grid(
            row=2, column=1, sticky=tk.W
        )
        fields.columnconfigure(1, weight=1)

        actions = ttk.Frame(outer)
        actions.pack(fill=tk.X, pady=14)
        ttk.Button(actions, text="1. Preview", command=self._preview).pack(side=tk.LEFT)
        self.apply_button = ttk.Button(
            actions, text="2. Organize previewed files", command=self._apply
        )
        self.apply_button.pack(side=tk.LEFT, padx=8)
        self.undo_button = ttk.Button(actions, text="Undo last run", command=self._undo_last)
        self.undo_button.pack(side=tk.LEFT)
        ttk.Button(actions, text="Choose journal to undo…", command=self._choose_undo).pack(
            side=tk.RIGHT
        )

        columns = ("status", "source", "destination", "rule")
        self.table = ttk.Treeview(outer, columns=columns, show="headings", selectmode="browse")
        for name, width in (("status", 80), ("source", 250), ("destination", 300), ("rule", 100)):
            self.table.heading(name, text=name.title())
            self.table.column(name, width=width, minwidth=70)
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        status_bar = ttk.Label(self.root, textvariable=self.status, padding=(16, 8), anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _input_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self.session.clear_preview()
        self.status.set("Inputs changed. Preview again before organizing.")
        self._sync_actions()

    def _choose_target(self) -> None:
        selected = filedialog.askdirectory(title="Choose a folder to organize")
        if selected:
            self.target.set(selected)
            self._input_changed()

    def _choose_config(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose rules",
            filetypes=(("JSON rules", "*.json"), ("All files", "*.*")),
        )
        if selected:
            self.config.set(selected)
            self._input_changed()

    def _preview(self) -> None:
        try:
            target = Path(self.target.get()) if self.target.get().strip() else Path.cwd()
            config = Path(self.config.get()) if self.config.get().strip() else None
            operations = self.session.preview(target, config)
            self._show(operations)
            movable = sum(item.status is Status.PLANNED for item in operations)
            skipped = sum(item.status is Status.SKIPPED for item in operations)
            self.status.set(
                f"Dry-run preview: {movable} file(s) ready, {skipped} skipped. No files moved."
            )
        except (ConfigError, PilotError, OSError) as exc:
            self.session.clear_preview()
            messagebox.showerror("Preview failed", str(exc), parent=self.root)
            self.status.set(f"Preview failed: {exc}")
        self._sync_actions()

    def _apply(self) -> None:
        movable = sum(item.status is Status.PLANNED for item in self.session.operations)
        if not messagebox.askyesno(
            "Organize previewed files?",
            f"Move {movable} file(s) exactly as shown?\n\n"
            "A journal will be saved so completed moves can be undone.",
            parent=self.root,
        ):
            return
        try:
            results, journal = self.session.apply_preview()
            self._show(results)
            failed = sum(item.status is Status.FAILED for item in results)
            moved = sum(item.status is Status.MOVED for item in results)
            self.status.set(f"Moved {moved} file(s); {failed} failed. Journal: {journal}")
            if failed:
                messagebox.showwarning(
                    "Finished with errors",
                    (
                        f"{failed} move(s) failed. No destination was overwritten.\\n\\n"
                        f"Journal: {journal}"
                    ),
                    parent=self.root,
                )
            else:
                messagebox.showinfo(
                    "Organization complete",
                    f"Moved {moved} file(s).\n\nUndo journal: {journal}",
                    parent=self.root,
                )
        except (PilotError, OSError) as exc:
            messagebox.showerror("Organization failed", str(exc), parent=self.root)
            self.status.set(f"Organization failed: {exc}")
        self._sync_actions()

    def _undo_last(self) -> None:
        self._undo(self.session.last_journal)

    def _choose_undo(self) -> None:
        journal_dir = default_data_dir() / "journals"
        selected = filedialog.askopenfilename(
            title="Choose an undo journal",
            initialdir=journal_dir if journal_dir.exists() else None,
            filetypes=(("Carrot File Pilot journal", "*.json"), ("All files", "*.*")),
        )
        if selected:
            self._undo(Path(selected))

    def _undo(self, journal: Path | None) -> None:
        if journal is None:
            return
        if not messagebox.askyesno(
            "Undo organized files?",
            (
                "Restore completed moves from this journal? "
                "Occupied original paths will be left alone."
            ),
            parent=self.root,
        ):
            return
        try:
            results = self.session.undo_journal(journal)
            self._show(results)
            failed = sum(item.status is Status.FAILED for item in results)
            restored = sum(item.status is Status.UNDONE for item in results)
            self.status.set(f"Restored {restored} file(s); {failed} failed.")
            if failed:
                messagebox.showwarning(
                    "Undo finished with errors",
                    f"Restored {restored} file(s). {failed} could not be restored; see the table.",
                    parent=self.root,
                )
            else:
                messagebox.showinfo(
                    "Undo complete", f"Restored {restored} file(s).", parent=self.root
                )
        except (PilotError, OSError) as exc:
            messagebox.showerror("Undo failed", str(exc), parent=self.root)
            self.status.set(f"Undo failed: {exc}")
        self._sync_actions()

    def _show(self, operations: list[Operation]) -> None:
        for item in self.table.get_children():
            self.table.delete(item)
        for item in operations:
            self.table.insert(
                "",
                tk.END,
                values=(
                    item.status.value,
                    str(item.source),
                    str(item.destination),
                    item.rule if item.detail is None else f"{item.rule}: {item.detail}",
                ),
            )

    def _sync_actions(self) -> None:
        movable = any(item.status is Status.PLANNED for item in self.session.operations)
        self.apply_button.configure(
            state=tk.NORMAL if self.session.preview_ready and movable else tk.DISABLED
        )
        self.undo_button.configure(
            state=tk.NORMAL if self.session.last_journal is not None else tk.DISABLED
        )


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    PilotWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
