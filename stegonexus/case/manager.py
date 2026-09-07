"""
Module 11 - Case Management, Reports Generation, Investigation Logs
==================================================================
Each investigation is a Case folder:

  <Workspace>/cases/<CaseID>/
      case.json          <- machine-readable case state + all findings
      reports/           <- generated Reports (MD / JSON / HTML)
      logs/investigation.log  <- timestamped investigation log

The Dashboard ties every Hiding/Extraction/Forensics action to the active
Case and appends it to the log automatically.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import uuid
from typing import Any, Dict, List, Optional


def _now() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _id() -> str:
    return "CASE-" + _dt.datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()


class CaseManager:
    """Open / create / save / close cases; persist findings; build reports."""

    def __init__(self, workspace: str):
        self.workspace = os.path.abspath(workspace)
        self.cases_dir = os.path.join(self.workspace, "cases")
        os.makedirs(self.cases_dir, exist_ok=True)
        self.case: Optional[Dict[str, Any]] = None
        self.case_dir: Optional[str] = None

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    def create_case(self, title: str, examiner: str = "", notes: str = "") -> dict:
        case = {
            "case_id": _id(),
            "title": title or "Untitled Case",
            "examiner": examiner,
            "notes": notes,
            "created": _now(),
            "updated": _now(),
            "status": "OPEN",
            "evidence": [],
            "findings": [],
            "operations": [],
            "logs": [],
        }
        self.case = case
        self.case_dir = os.path.join(self.cases_dir, case["case_id"])
        os.makedirs(os.path.join(self.case_dir, "reports"), exist_ok=True)
        os.makedirs(os.path.join(self.case_dir, "logs"), exist_ok=True)
        self.save()
        self.log("case created", detail=case["title"])
        return case

    def open_case(self, case_id: str) -> dict:
        path = os.path.join(self.cases_dir, case_id, "case.json")
        with open(path, "r", encoding="utf-8") as fh:
            self.case = json.load(fh)
        self.case_dir = os.path.dirname(path)
        return self.case

    def list_cases(self) -> List[dict]:
        out = []
        for name in sorted(os.listdir(self.cases_dir)):
            p = os.path.join(self.cases_dir, name, "case.json")
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as fh:
                        c = json.load(fh)
                    out.append({"case_id": c["case_id"], "title": c["title"],
                                "created": c["created"], "status": c["status"]})
                except Exception:
                    continue
        return out

    def close_case(self) -> dict:
        if not self.case:
            raise RuntimeError("No open case")
        self.case["status"] = "CLOSED"
        self.case["updated"] = _now()
        self.log("case closed")
        self.save()
        return self.case

    def save(self) -> None:
        if self.case and self.case_dir:
            with open(os.path.join(self.case_dir, "case.json"), "w", encoding="utf-8") as fh:
                json.dump(self.case, fh, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------ #
    # case content
    # ------------------------------------------------------------------ #
    def add_evidence(self, path: str, category: str = "artifact",
                     description: str = "") -> dict:
        entry = {"id": f"EV-{len(self.case['evidence']) + 1:03d}",
                 "path": os.path.abspath(path), "category": category,
                 "description": description, "added": _now(),
                 "sha256": _sha256_of_file(path)}
        self.case["evidence"].append(entry)
        self.log("evidence added", detail=f"{entry['id']} {path}")
        self.save()
        return entry

    def add_finding(self, category: str, summary: str, details: Any = None,
                    severity: str = "INFO") -> dict:
        entry = {"id": f"FN-{len(self.case['findings']) + 1:03d}",
                 "category": category, "summary": summary,
                 "details": details, "severity": severity,
                 "timestamp": _now()}
        self.case["findings"].append(entry)
        self.case["updated"] = _now()
        self.log("finding recorded", detail=f"[{severity}] {summary}")
        self.save()
        return entry

    def record_operation(self, module: str, action: str, result: Dict[str, Any]) -> None:
        entry = {"timestamp": _now(), "module": module, "action": action,
                 "result": _jsonable(result)}
        self.case["operations"].append(entry)
        self.case["updated"] = _now()
        self.log(f"operation: {module} {action}")
        self.save()

    def log(self, message: str, detail: str = "") -> None:
        if self.case is None:
            return
        entry = {"timestamp": _now(), "message": message, "detail": detail}
        self.case["logs"].append(entry)
        log_path = os.path.join(self.case_dir, "logs", "investigation.log")
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"[{entry['timestamp']}] {message}"
                     + (f" :: {detail}" if detail else "") + "\n")
        self.case["updated"] = _now()

    # ------------------------------------------------------------------ #
    # reports
    # ------------------------------------------------------------------ #
    def export_report(self, fmt: str = "md") -> str:
        if not self.case:
            raise RuntimeError("No open case")
        reports = os.path.join(self.case_dir, "reports")
        os.makedirs(reports, exist_ok=True)
        if fmt == "json":
            path = os.path.join(reports, "report_case.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.case, fh, indent=2, ensure_ascii=False)
        elif fmt == "html":
            path = os.path.join(reports, "report_case.html")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._render_html())
        else:
            path = os.path.join(reports, "report_case.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._render_md())
        self.log("report exported", detail=f"{fmt} -> {path}")
        return path

    def _render_md(self) -> str:
        c = self.case
        lines = [
            f"# StegoNexus Investigation Report",
            "",
            f"**Case ID:** {c['case_id']}  ",
            f"**Title:** {c['title']}  ",
            f"**Examiner:** {c['examiner'] or '-'}  ",
            f"**Status:** {c['status']}  ",
            f"**Created:** {c['created']}  ",
            f"**Updated:** {c['updated']}",
            "",
            "## Evidence",
            "",
        ]
        for ev in c["evidence"]:
            lines.append(f"- `{ev['id']}` {ev['path']} ({ev['category']})"
                         f"  \n  SHA-256: `{ev['sha256'][:32]}...`")
        lines += ["", "## Findings", ""]
        for f in c["findings"]:
            lines.append(f"- **[{f['severity']}] {f['summary']}** "
                         f"({f['category']}, {f['timestamp']})")
        lines += ["", "## Operations Log", ""]
        for op in c["operations"]:
            lines.append(f"- `{op['timestamp']}` {op['module']} / {op['action']}")
        lines += ["", "## Investigation Log", ""]
        for lg in c["logs"][-100:]:
            lines.append(f"- `{lg['timestamp']}` {lg['message']}"
                         + (f" :: {lg['detail']}" if lg["detail"] else ""))
        lines += ["", "---", "*Generated by StegoNexus — Unified Hiding, "
                          "Extraction & Forensics Framework*", ""]
        return "\n".join(lines)

    def _render_html(self) -> str:
        md = self._render_md()
        # minimal escape + paragraph rendering
        import html as _h
        body = _h.escape(md)
        body = re.sub(r"^### (.+)$", r"<h3>\1</h3>", body, flags=re.M)
        body = re.sub(r"^## (.+)$", r"<h2>\1</h2>", body, flags=re.M)
        body = re.sub(r"^# (.+)$", r"<h1>\1</h1>", body, flags=re.M)
        body = re.sub(r"^- (.+)$", r"<li>\1</li>", body, flags=re.M)
        body = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", body)
        body = body.replace("\n\n", "</p><p>").replace("\n", "<br>")
        return (f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
                f"<title>StegoNexus Report</title>"
                f"<style>body{{font-family:sans-serif;max-width:900px;"
                f"margin:2rem auto;padding:0 1rem;background:#0f1117;"
                f"color:#e6e6e6}}h1{{color:#00d98b}}li{{margin:.3rem 0}}"
                f"</style></head><body><p>{body}</p></body></html>")


def _jsonable(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return str(obj)


def _sha256_of_file(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


__all__ = ["CaseManager"]
