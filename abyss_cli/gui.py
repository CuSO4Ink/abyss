"""Abyss Dashboard — Native tkinter GUI (R096).

Pure Python stdlib (tkinter + ttk + threading). Zero external dependencies.
Creates a native Windows desktop window with read-only dashboard panels.

Architecture:
    tkinter root (main thread)
        -> after() polling loop reads data queue
    DataCollector (background thread)
        -> calls existing core functions (summary, brain, adapter, etc.)

All panels are read-only in Phase A. No writes, no execution, no approval.
"""
from __future__ import annotations

import json
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
#  Data collection (background thread)
# ---------------------------------------------------------------------------

def _safe_call(func, *args, **kwargs) -> Any:
    """Call a function, return (ok, result_or_error)."""
    try:
        return True, func(*args, **kwargs)
    except Exception as exc:
        return False, str(exc)


def collect_all() -> dict[str, Any]:
    """Collect all dashboard data from existing core functions.

    Each section is independently error-isolated so one failure
    doesn't break the entire dashboard.
    """
    data: dict[str, Any] = {}
    data["_collected_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- Summary / operations health ---
    ok, result = _safe_call(
        lambda: __import__("abyss_cli.summary", fromlist=["build_summary"]).build_summary(include_check=False)
    )
    data["summary"] = result if ok else {"error": result}

    # --- Integrity ---
    ok, result = _safe_call(
        lambda: __import__("abyss_cli.integrity", fromlist=["run_checks"]).run_checks()
    )
    data["integrity"] = {"ok": result[0], "messages": result[1]} if ok else {"error": result, "ok": False}

    # --- Brain context (FSM, health, outbox, assessment, CLI commands) ---
    ok, result = _safe_call(
        lambda: __import__("abyss_cli.brain", fromlist=["build_brain_context"]).build_brain_context()
    )
    data["brain_context"] = result if ok else {"error": result}

    # --- Brain working memory ---
    ok, result = _safe_call(
        lambda: __import__("abyss_cli.brain", fromlist=["load_working_memory"]).load_working_memory(limit=50)
    )
    data["working_memory"] = result if ok else []

    # --- Memory records (directions/decisions) ---
    ok, result = _safe_call(
        lambda: __import__("abyss_cli.memory", fromlist=["list_memory_records"]).list_memory_records()
    )
    data["memory_records"] = result if ok else []

    # --- Outbox needs ---
    ok, result = _safe_call(
        lambda: __import__("abyss_cli.external_adapter", fromlist=["list_needs"]).list_needs()
    )
    data["outbox_needs"] = result if ok else []

    # --- Evolution records ---
    ok, result = _safe_call(
        lambda: __import__("abyss_cli.evolution", fromlist=["list_evolution_records"]).list_evolution_records()
    )
    data["evolution_records"] = result if ok else []

    # --- Workflows ---
    ok, result = _safe_call(
        lambda: __import__("abyss_cli.workflow", fromlist=["list_workflows"]).list_workflows()
    )
    data["workflows"] = result if ok else []

    # --- Owner inbox ---
    ok, result = _safe_call(
        lambda: __import__("abyss_cli.owner", fromlist=["list_owner_items"]).list_owner_items(include_closed=False)
    )
    data["owner_items"] = result if ok else []

    # --- Git status ---
    ok, result = _safe_call(
        lambda: __import__("abyss_cli.utils", fromlist=["run_git"]).run_git(
            ["status", "--short", "--branch"], allow_fail=True
        )
    )
    data["git_status"] = result.strip() if ok else ""

    return data


class DataCollector(threading.Thread):
    """Background thread that periodically collects dashboard data.

    Puts results into a queue. The main tkinter thread polls the queue
    via after() and updates widgets. This keeps the UI responsive.
    """

    def __init__(self, data_queue: queue.Queue, interval: float = 8.0, daemon: bool = True):
        super().__init__(daemon=daemon)
        self._queue = data_queue
        self._interval = interval
        self._stop = threading.Event()

    def run(self) -> None:
        # First collect immediately
        self._collect_once()
        while not self._stop.is_set():
            self._stop.wait(self._interval)
            if self._stop.is_set():
                break
            self._collect_once()

    def _collect_once(self) -> None:
        try:
            data = collect_all()
            self._queue.put(("data", data))
        except Exception as exc:
            self._queue.put(("error", str(exc)))

    def stop(self) -> None:
        self._stop.set()


# ---------------------------------------------------------------------------
#  UI Helpers
# ---------------------------------------------------------------------------

def _truncate(text: str, limit: int = 200) -> str:
    if not text:
        return ""
    text = str(text)
    return text[:limit] + "..." if len(text) > limit else text


def _status_color(ok: bool) -> str:
    return "#2e7d32" if ok else "#c62828"  # green / red


def _need_status_color(status: str) -> str:
    colors = {
        "pending": "#f57f17",   # amber
        "fulfilled": "#2e7d32",  # green
        "failed": "#c62828",     # red
    }
    return colors.get(status, "#757575")


def _workflow_status_color(status: str) -> str:
    colors = {
        "done": "#2e7d32",
        "failed": "#c62828",
        "blocked": "#f57f17",
        "rejected": "#c62828",
        "superseded": "#757575",
    }
    return colors.get(status, "#1565c0")


# ---------------------------------------------------------------------------
#  Dashboard Tabs
# ---------------------------------------------------------------------------

class SystemTab(ttk.Frame):
    """System overview: integrity, FSM, operations health, git status."""

    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        # --- Top status bar ---
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        self._integrity_label = ttk.Label(top, text="Integrity: ...", font=("Segoe UI", 11, "bold"))
        self._integrity_label.pack(side="left", padx=(0, 20))

        self._fsm_label = ttk.Label(top, text="FSM: ...", font=("Segoe UI", 11, "bold"))
        self._fsm_label.pack(side="left", padx=(0, 20))

        self._phase_label = ttk.Label(top, text="Phase: ...", font=("Segoe UI", 11))
        self._phase_label.pack(side="left", padx=(0, 20))

        self._updated_label = ttk.Label(top, text="", font=("Segoe UI", 9))
        self._updated_label.pack(side="right")

        # --- Operations health grid ---
        health_frame = ttk.LabelFrame(self, text="Operations Health", padding=10)
        health_frame.pack(fill="x", padx=10, pady=5)

        self._health_labels: dict[str, ttk.Label] = {}
        health_keys = [
            "active_workflows", "pending_owner_items", "true_failures",
            "true_blocked", "expected_governance_blocks", "provider_empty_or_timeout",
            "implementation_pipeline_issues", "invalid_changesets",
        ]
        for i, key in enumerate(health_keys):
            row, col = divmod(i, 4)
            ttk.Label(health_frame, text=key.replace("_", " ").title()).grid(
                row=row, column=col * 2, sticky="w", padx=(0, 5), pady=2
            )
            lbl = ttk.Label(health_frame, text="-", font=("Segoe UI", 11, "bold"))
            lbl.grid(row=row, column=col * 2 + 1, sticky="w", padx=(0, 15), pady=2)
            self._health_labels[key] = lbl

        # --- Changeset summary ---
        cs_frame = ttk.LabelFrame(self, text="Changesets", padding=10)
        cs_frame.pack(fill="x", padx=10, pady=5)

        self._cs_labels: dict[str, ttk.Label] = {}
        cs_keys = ["total", "proposed", "approved", "applied", "invalid"]
        for i, key in enumerate(cs_keys):
            ttk.Label(cs_frame, text=key.title()).grid(row=0, column=i * 2, sticky="w", padx=(0, 5))
            lbl = ttk.Label(cs_frame, text="-", font=("Segoe UI", 11, "bold"))
            lbl.grid(row=0, column=i * 2 + 1, sticky="w", padx=(0, 15))
            self._cs_labels[key] = lbl

        # --- Git status ---
        git_frame = ttk.LabelFrame(self, text="Git Status", padding=10)
        git_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self._git_text = scrolledtext.ScrolledText(git_frame, height=6, wrap="word",
                                                     font=("Consolas", 10), state="disabled")
        self._git_text.pack(fill="both", expand=True)

        # --- Integrity messages ---
        msg_frame = ttk.LabelFrame(self, text="Integrity Messages", padding=10)
        msg_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self._msg_text = scrolledtext.ScrolledText(msg_frame, height=4, wrap="word",
                                                     font=("Consolas", 10), state="disabled")
        self._msg_text.pack(fill="both", expand=True)

    def update(self, data: dict[str, Any]) -> None:
        # Integrity
        integrity = data.get("integrity", {})
        ok = integrity.get("ok", False)
        self._integrity_label.config(
            text=f"Integrity: {'OK' if ok else 'FAIL'}",
            foreground=_status_color(ok),
        )

        # FSM
        ctx = data.get("brain_context", {})
        fsm = ctx.get("fsm_state", {})
        fsm_state = fsm.get("state", "unknown")
        fsm_available = fsm.get("available", False)
        self._fsm_label.config(
            text=f"FSM: {fsm_state}" if fsm_available else "FSM: n/a",
            foreground=_status_color(fsm_state != "needs_attention") if fsm_available else "#757575",
        )

        # Phase
        summary = data.get("summary", {})
        health = summary.get("operations_health_counts", {})
        phase = "stable" if ok and health.get("active_workflows", 0) == 0 else "needs_attention"
        self._phase_label.config(
            text=f"Phase: {phase}",
            foreground=_status_color(phase == "stable"),
        )

        self._updated_label.config(text=f"Updated: {data.get('_collected_at', '')}")

        # Health counts
        for key, lbl in self._health_labels.items():
            val = health.get(key, 0)
            lbl.config(text=str(val))
            if key in ("true_failures", "true_blocked", "invalid_changesets") and val and val > 0:
                lbl.config(foreground="#c62828")
            elif key in ("active_workflows", "pending_owner_items") and val and val > 0:
                lbl.config(foreground="#f57f17")
            else:
                lbl.config(foreground="#2e7d32" if val == 0 or not val else "#1565c0")

        # Changesets
        cs = summary.get("changesets", {})
        for key, lbl in self._cs_labels.items():
            lbl.config(text=str(cs.get(key, 0)))

        # Git status
        git_status = data.get("git_status", "")
        self._git_text.config(state="normal")
        self._git_text.delete("1.0", "end")
        self._git_text.insert("1.0", git_status or "(clean)")
        self._git_text.config(state="disabled")

        # Integrity messages
        messages = integrity.get("messages", [])
        self._msg_text.config(state="normal")
        self._msg_text.delete("1.0", "end")
        self._msg_text.insert("1.0", "\n".join(messages) if messages else "(no messages)")
        self._msg_text.config(state="disabled")


class BrainTab(ttk.Frame):
    """Brain Agent: working memory, assessment, direction alignment."""

    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        # --- Assessment ---
        assess_frame = ttk.LabelFrame(self, text="System Assessment", padding=10)
        assess_frame.pack(fill="x", padx=10, pady=5)

        self._assess_text = scrolledtext.ScrolledText(assess_frame, height=5, wrap="word",
                                                        font=("Segoe UI", 10), state="disabled")
        self._assess_text.pack(fill="both", expand=True)

        # --- Direction alignment ---
        dir_frame = ttk.LabelFrame(self, text="Direction Alignment (Memory Layer)", padding=10)
        dir_frame.pack(fill="x", padx=10, pady=5)

        self._dir_info = ttk.Label(dir_frame, text="", font=("Segoe UI", 10))
        self._dir_info.pack(anchor="w")

        self._dir_tree = ttk.Treeview(dir_frame, columns=("id", "title", "created"), height=6,
                                       show="headings")
        self._dir_tree.heading("id", text="ID")
        self._dir_tree.heading("title", text="Title")
        self._dir_tree.heading("created", text="Created")
        self._dir_tree.column("id", width=140)
        self._dir_tree.column("title", width=300)
        self._dir_tree.column("created", width=160)
        self._dir_tree.pack(fill="both", expand=True, pady=(5, 0))

        # --- Working memory ---
        wm_frame = ttk.LabelFrame(self, text="Brain Working Memory (Recent Cognitive Outputs)", padding=10)
        wm_frame.pack(fill="both", expand=True, padx=10, pady=5)

        wm_cols = ("timestamp", "kind", "question", "excerpt")
        self._wm_tree = ttk.Treeview(wm_frame, columns=wm_cols, height=10, show="headings")
        self._wm_tree.heading("timestamp", text="Timestamp")
        self._wm_tree.heading("kind", text="Kind")
        self._wm_tree.heading("question", text="Question")
        self._wm_tree.heading("excerpt", text="Excerpt")
        self._wm_tree.column("timestamp", width=160)
        self._wm_tree.column("kind", width=140)
        self._wm_tree.column("question", width=200)
        self._wm_tree.column("excerpt", width=400)
        self._wm_tree.pack(fill="both", expand=True)

    def update(self, data: dict[str, Any]) -> None:
        # Assessment
        ctx = data.get("brain_context", {})
        assessment = ctx.get("assessment", [])
        self._assess_text.config(state="normal")
        self._assess_text.delete("1.0", "end")
        self._assess_text.insert("1.0", "\n".join(f"- {a}" for a in assessment) if assessment else "(no assessment)")
        self._assess_text.config(state="disabled")

        # Direction alignment
        alignment = ctx.get("direction_alignment", {})
        dir_count = alignment.get("direction_count", 0)
        dec_count = alignment.get("decision_count", 0)
        notes = alignment.get("consistency_notes", [])
        self._dir_info.config(
            text=f"Directions: {dir_count}  |  Decisions: {dec_count}  |  Notes: {'; '.join(notes[:2])}"
        )

        # Clear and repopulate direction tree
        for item in self._dir_tree.get_children():
            self._dir_tree.delete(item)

        directions = alignment.get("recent_directions", [])
        decisions = alignment.get("recent_decisions", [])
        for record in directions:
            self._dir_tree.insert("", "end", values=(
                record.get("id", ""),
                f"[DIR] {record.get('title', '')}",
                record.get("created_at", ""),
            ))
        for record in decisions:
            self._dir_tree.insert("", "end", values=(
                record.get("id", ""),
                f"[DEC] {record.get('title', '')}",
                record.get("created_at", ""),
            ))

        # Working memory
        for item in self._wm_tree.get_children():
            self._wm_tree.delete(item)

        wm_entries = data.get("working_memory", [])
        for entry in wm_entries:
            self._wm_tree.insert("", "end", values=(
                entry.get("timestamp", "")[:19],
                entry.get("kind", ""),
                _truncate(entry.get("question", "") or "", 80),
                _truncate(entry.get("text", ""), 200),
            ))


class OutboxTab(ttk.Frame):
    """Outbox needs with status indicators."""

    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        # --- Summary stats ---
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        self._total_label = ttk.Label(top, text="Total: -", font=("Segoe UI", 11, "bold"))
        self._total_label.pack(side="left", padx=(0, 20))
        self._pending_label = ttk.Label(top, text="Pending: -", font=("Segoe UI", 11, "bold"))
        self._pending_label.pack(side="left", padx=(0, 20))
        self._fulfilled_label = ttk.Label(top, text="Fulfilled: -", font=("Segoe UI", 11, "bold"))
        self._fulfilled_label.pack(side="left", padx=(0, 20))
        self._failed_label = ttk.Label(top, text="Failed: -", font=("Segoe UI", 11, "bold"))
        self._failed_label.pack(side="left", padx=(0, 20))

        # --- Needs tree ---
        tree_frame = ttk.LabelFrame(self, text="Outbox Needs", padding=10)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        cols = ("id", "type", "status", "created_by", "created_at")
        self._tree = ttk.Treeview(tree_frame, columns=cols, height=15, show="headings")
        self._tree.heading("id", text="Need ID")
        self._tree.heading("type", text="Type")
        self._tree.heading("status", text="Status")
        self._tree.heading("created_by", text="Created By")
        self._tree.heading("created_at", text="Created At")
        self._tree.column("id", width=160)
        self._tree.column("type", width=200)
        self._tree.column("status", width=100)
        self._tree.column("created_by", width=120)
        self._tree.column("created_at", width=160)

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Tag colors
        self._tree.tag_configure("pending", foreground="#f57f17")
        self._tree.tag_configure("fulfilled", foreground="#2e7d32")
        self._tree.tag_configure("failed", foreground="#c62828")

        # --- Detail pane ---
        detail_frame = ttk.LabelFrame(self, text="Need Detail (select a row above)", padding=10)
        detail_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self._detail_text = scrolledtext.ScrolledText(detail_frame, height=6, wrap="word",
                                                        font=("Consolas", 10), state="disabled")
        self._detail_text.pack(fill="both", expand=True)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        self._needs_data: list[dict[str, Any]] = []

    def _on_select(self, _event):
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0], "values")
        need_id = values[0] if values else ""
        for need in self._needs_data:
            if need.get("id") == need_id:
                self._detail_text.config(state="normal")
                self._detail_text.delete("1.0", "end")
                self._detail_text.insert("1.0", json.dumps(need, indent=2, default=str, ensure_ascii=False))
                self._detail_text.config(state="disabled")
                return

    def update(self, data: dict[str, Any]) -> None:
        needs = data.get("outbox_needs", [])
        self._needs_data = needs

        counts = {"pending": 0, "fulfilled": 0, "failed": 0}
        for n in needs:
            status = n.get("lifecycle", {}).get("status", "unknown")
            counts[status] = counts.get(status, 0) + 1

        self._total_label.config(text=f"Total: {len(needs)}")
        self._pending_label.config(text=f"Pending: {counts.get('pending', 0)}", foreground="#f57f17")
        self._fulfilled_label.config(text=f"Fulfilled: {counts.get('fulfilled', 0)}", foreground="#2e7d32")
        self._failed_label.config(text=f"Failed: {counts.get('failed', 0)}", foreground="#c62828")

        for item in self._tree.get_children():
            self._tree.delete(item)

        for need in needs:
            lc = need.get("lifecycle", {})
            status = lc.get("status", "unknown")
            self._tree.insert("", "end", values=(
                need.get("id", ""),
                need.get("type", ""),
                status,
                need.get("created_by", ""),
                lc.get("created_at", "")[:19],
            ), tags=(status,))


class EvolutionTab(ttk.Frame):
    """Evolution requests and proposals."""

    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        # --- Records tree ---
        frame = ttk.LabelFrame(self, text="Evolution Records (Requests + Proposals)", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("kind", "id", "status", "summary", "path")
        self._tree = ttk.Treeview(frame, columns=cols, height=15, show="headings")
        self._tree.heading("kind", text="Kind")
        self._tree.heading("id", text="ID")
        self._tree.heading("status", text="Status")
        self._tree.heading("summary", text="Summary")
        self._tree.heading("path", text="Path")
        self._tree.column("kind", width=90)
        self._tree.column("id", width=160)
        self._tree.column("status", width=120)
        self._tree.column("summary", width=350)
        self._tree.column("path", width=250)

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._tree.tag_configure("request", foreground="#1565c0")
        self._tree.tag_configure("proposal", foreground="#6a1b9a")

        # --- Owner inbox ---
        owner_frame = ttk.LabelFrame(self, text="Owner Inbox (Pending Items)", padding=10)
        owner_frame.pack(fill="both", expand=True, padx=10, pady=5)

        owner_cols = ("id", "type", "status", "target_id", "title")
        self._owner_tree = ttk.Treeview(owner_frame, columns=owner_cols, height=6, show="headings")
        self._owner_tree.heading("id", text="Item ID")
        self._owner_tree.heading("type", text="Type")
        self._owner_tree.heading("status", text="Status")
        self._owner_tree.heading("target_id", text="Target")
        self._owner_tree.heading("title", text="Title")
        self._owner_tree.column("id", width=140)
        self._owner_tree.column("type", width=100)
        self._owner_tree.column("status", width=80)
        self._owner_tree.column("target_id", width=140)
        self._owner_tree.column("title", width=300)
        self._owner_tree.pack(fill="both", expand=True)

        # --- Workflow summary ---
        wf_frame = ttk.LabelFrame(self, text="Recent Workflows", padding=10)
        wf_frame.pack(fill="both", expand=True, padx=10, pady=5)

        wf_cols = ("id", "status", "roadmap_id", "summary")
        self._wf_tree = ttk.Treeview(wf_frame, columns=wf_cols, height=6, show="headings")
        self._wf_tree.heading("id", text="Workflow ID")
        self._wf_tree.heading("status", text="Status")
        self._wf_tree.heading("roadmap_id", text="Roadmap")
        self._wf_tree.heading("summary", text="Summary")
        self._wf_tree.column("id", width=140)
        self._wf_tree.column("status", width=100)
        self._wf_tree.column("roadmap_id", width=120)
        self._wf_tree.column("summary", width=300)
        self._wf_tree.pack(fill="both", expand=True)

        self._wf_tree.tag_configure("done", foreground="#2e7d32")
        self._wf_tree.tag_configure("failed", foreground="#c62828")
        self._wf_tree.tag_configure("blocked", foreground="#f57f17")

    def update(self, data: dict[str, Any]) -> None:
        # Evolution records
        records = data.get("evolution_records", [])
        for item in self._tree.get_children():
            self._tree.delete(item)
        for rec in records:
            kind = rec.get("kind", "")
            self._tree.insert("", "end", values=(
                kind,
                rec.get("id", ""),
                rec.get("status", ""),
                _truncate(rec.get("summary", ""), 80),
                rec.get("path", ""),
            ), tags=(kind,))

        # Owner items
        owner_items = data.get("owner_items", [])
        for item in self._owner_tree.get_children():
            self._owner_tree.delete(item)
        for item in owner_items:
            self._owner_tree.insert("", "end", values=(
                item.get("id", ""),
                item.get("type", ""),
                item.get("status", ""),
                item.get("target_id", ""),
                _truncate(item.get("title", ""), 80),
            ))

        # Workflows
        workflows = data.get("workflows", [])
        for item in self._wf_tree.get_children():
            self._wf_tree.delete(item)
        # Show most recent first, limit to 20
        sorted_wf = sorted(workflows, key=lambda w: w.get("updated_at", ""), reverse=True)[:20]
        for wf in sorted_wf:
            status = wf.get("status", "")
            self._wf_tree.insert("", "end", values=(
                wf.get("id", ""),
                status,
                wf.get("roadmap_id", ""),
                _truncate(wf.get("summary", ""), 80),
            ), tags=(status,))


class CLITab(ttk.Frame):
    """CLI command reference tree."""

    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        frame = ttk.LabelFrame(self, text="Available CLI Commands", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._tree = ttk.Treeview(frame, columns=("subcommands",), height=20, show="tree headings")
        self._tree.heading("#0", text="Command")
        self._tree.heading("subcommands", text="Subcommands")
        self._tree.column("#0", width=200)
        self._tree.column("subcommands", width=500)
        self._tree.pack(fill="both", expand=True)

        info_frame = ttk.Frame(self, padding=(10, 5))
        info_frame.pack(fill="x")
        self._info_label = ttk.Label(info_frame,
                                      text="These commands are available via: python -m abyss_cli <command> [subcommand]",
                                      font=("Segoe UI", 9))
        self._info_label.pack(anchor="w")

    def update(self, data: dict[str, Any]) -> None:
        ctx = data.get("brain_context", {})
        commands = ctx.get("cli_commands", [])
        for item in self._tree.get_children():
            self._tree.delete(item)
        for cmd in commands:
            name = cmd.get("command", "")
            subs = cmd.get("subcommands", [])
            sub_str = ", ".join(subs) if subs else "(no subcommands)"
            self._tree.insert("", "end", text=name, values=(sub_str,))


# ---------------------------------------------------------------------------
#  Main Dashboard Window
# ---------------------------------------------------------------------------

class AbyssDashboard(tk.Tk):
    """Main native dashboard window."""

    def __init__(self, refresh_interval: float = 8.0):
        super().__init__()
        self.title("Abyss Dashboard")
        self.geometry("1100x750")
        self.minsize(900, 600)

        # Style
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=22)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

        # Header
        header = ttk.Frame(self, padding=(10, 5))
        header.pack(fill="x")
        ttk.Label(header, text="Abyss Dashboard", font=("Segoe UI", 14, "bold")).pack(side="left")
        self._status_label = ttk.Label(header, text="Loading...", font=("Segoe UI", 9))
        self._status_label.pack(side="right")

        # Notebook with tabs
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self._system_tab = SystemTab(self._notebook)
        self._brain_tab = BrainTab(self._notebook)
        self._outbox_tab = OutboxTab(self._notebook)
        self._evolution_tab = EvolutionTab(self._notebook)
        self._cli_tab = CLITab(self._notebook)

        self._notebook.add(self._system_tab, text="System")
        self._notebook.add(self._brain_tab, text="Brain")
        self._notebook.add(self._outbox_tab, text="Outbox")
        self._notebook.add(self._evolution_tab, text="Evolution")
        self._notebook.add(self._cli_tab, text="CLI Ref")

        # Data queue and collector thread
        self._data_queue: queue.Queue = queue.Queue()
        self._collector = DataCollector(self._data_queue, interval=refresh_interval)
        self._collector.start()

        # Start polling
        self.after(500, self._poll_queue)

        # Clean shutdown
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _poll_queue(self) -> None:
        """Poll the data queue and update visible tabs."""
        try:
            while True:
                kind, payload = self._data_queue.get_nowait()
                if kind == "data":
                    self._update_tabs(payload)
                    self._status_label.config(text=f"Last update: {payload.get('_collected_at', '')}")
                elif kind == "error":
                    self._status_label.config(text=f"Error: {payload[:60]}")
        except queue.Empty:
            pass
        self.after(2000, self._poll_queue)

    def _update_tabs(self, data: dict[str, Any]) -> None:
        """Update all tabs with fresh data."""
        self._system_tab.update(data)
        self._brain_tab.update(data)
        self._outbox_tab.update(data)
        self._evolution_tab.update(data)
        self._cli_tab.update(data)

    def _on_close(self) -> None:
        self._collector.stop()
        self.destroy()


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------

def launch(refresh_interval: float = 8.0) -> None:
    """Launch the Abyss native dashboard window."""
    app = AbyssDashboard(refresh_interval=refresh_interval)
    app.mainloop()
