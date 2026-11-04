#!/usr/bin/env python3
"""Measured token usage per Claude Code session, read from the local session logs.

Claude Code writes every session to ~/.claude/projects/<project>/<session>.jsonl.
Each assistant message carries the API `usage` block, so these numbers are real,
not estimates. Output: one TU1 line per session, ready to paste into the Token Map.

Usage:
  python3 claude_code_usage.py                 # last 7 days
  python3 claude_code_usage.py --days 30
  python3 claude_code_usage.py --days 7 --json # raw rows for Claude to classify
  python3 claude_code_usage.py --days 3 --sync DIR
      merge the last 3 days into the Token Map month documents saved in DIR
      (read with ArtifactData out_dir), write the merged ones to DIR/merged/<YYYY-MM>.json
"""
import argparse
import glob
import json
import os
import re
from datetime import datetime, timedelta, timezone

PURPOSE_HINTS = [  # first match wins; Claude may override after reading the prompt
    ("media", r"video|reel|render|recap|hyperframes|ảnh|image|voice|tts|thumbnail"),
    ("slides", r"slide|pptx|deck|thuyết trình|trình chiếu"),
    ("docs", r"docx|\bdoc\b|báo cáo|report|tài liệu|bài giảng|proposal"),
    ("email", r"email|e-mail|thư|reply|caption"),
    ("data", r"csv|excel|xlsx|data|dữ liệu|dashboard|chart|biểu đồ|sql"),
    ("research", r"research|tìm hiểu|nghiên cứu|so sánh|search"),
]


def guess_purpose(text):
    low = (text or "").lower()
    for code, pat in PURPOSE_HINTS:
        if re.search(pat, low):
            return code
    return "code"


def first_prompt(content):
    if isinstance(content, list):
        content = " ".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
    content = (content or "").strip()
    m = re.match(r'<scheduled-task name="([^"]+)"', content)
    if m:
        return "scheduled task " + m.group(1)
    m = re.match(r"Base directory for this skill: (\S+)", content)
    if m:
        return "skill " + os.path.basename(m.group(1).rstrip("/"))
    m = re.search(r"<command-name>/?([^<]+)</command-name>", content)
    if m:
        return "/" + m.group(1).strip()
    if not content or content.startswith("<"):  # other system wrappers
        return ""
    return re.sub(r"\s+", " ", content)[:120]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sync", metavar="DIR", help="merge into Token Map month docs found under DIR")
    ap.add_argument("--root", default=os.path.expanduser("~/.claude/projects"))
    a = ap.parse_args()
    since = datetime.now(timezone.utc) - timedelta(days=a.days)

    sessions, seen = {}, set()
    for path in glob.glob(os.path.join(a.root, "**", "*.jsonl"), recursive=True):
        try:
            fh = open(path, encoding="utf-8")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                ts, sid = d.get("timestamp"), d.get("sessionId")
                if not ts or not sid:
                    continue
                t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if t < since:
                    continue
                s = sessions.setdefault(sid, {"session": sid, "start": t, "project": os.path.basename(d.get("cwd") or ""),
                                              "prompt": "", "tokens": 0, "cached": 0, "output": 0, "models": set()})
                s["start"] = min(s["start"], t)
                if not s["project"] and d.get("cwd"):
                    s["project"] = os.path.basename(d["cwd"])
                msg = d.get("message") or {}
                if d.get("type") == "user" and not s["prompt"] and not d.get("isSidechain"):
                    s["prompt"] = first_prompt(msg.get("content"))
                u = msg.get("usage")
                if d.get("type") == "assistant" and u:
                    key = msg.get("id") or d.get("requestId") or d.get("uuid")
                    if key in seen:  # one API reply is logged once per content block
                        continue
                    seen.add(key)
                    s["tokens"] += u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("output_tokens", 0)
                    s["cached"] += u.get("cache_read_input_tokens", 0)
                    s["output"] += u.get("output_tokens", 0)
                    if msg.get("model"):
                        s["models"].add(msg["model"])

    rows = []
    for s in sorted(sessions.values(), key=lambda x: x["start"]):
        if not s["tokens"] and not s["cached"]:
            continue
        rows.append({
            "date": s["start"].astimezone().strftime("%Y-%m-%d"),
            "session": s["session"], "project": s["project"], "prompt": s["prompt"],
            "purpose_guess": guess_purpose(s["prompt"] + " " + s["project"]),
            "tokens": s["tokens"], "cached": s["cached"], "output": s["output"], "models": sorted(s["models"]),
        })

    if a.sync:
        sync(rows, a.sync)
        return
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    print(f"{len(rows)} Claude Code sessions in the last {a.days} days")
    print(f"Total: {sum(r['tokens'] for r in rows):,} tokens (+ {sum(r['cached'] for r in rows):,} read from cache)\n")
    for r in rows:
        note = (r["project"] + ": " + r["prompt"]).replace("|", "/")[:80]
        print(f"TU1|date={r['date']}|env=code|purpose={r['purpose_guess']}|tokens={r['tokens']}|cached={r['cached']}|src=do|sid={r['session']}|note={note}")


def load_month_docs(root):
    """Month docs as ArtifactData saved them; accepts a bare body or one wrapped with metadata."""
    docs = {}
    for path in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
        name = os.path.basename(path)[:-5]
        if "merged" in path.split(os.sep) or not re.fullmatch(r"\d{4}-\d{2}", name):
            continue
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        body = d.get("data") if isinstance(d.get("data"), dict) else d
        docs[name] = {"entries": body.get("entries", []), "version": d.get("version")}
    return docs


def sync(rows, root):
    docs = load_month_docs(root)
    changed = {}
    for r in rows:
        m = r["date"][:7]
        doc = docs.setdefault(m, {"entries": [], "version": None})
        e = {"id": "cc-" + r["session"], "sid": r["session"], "date": r["date"], "env": "code",
             "purpose": r["purpose_guess"], "tokens": r["tokens"], "cached": r["cached"], "src": "do",
             "note": (r["project"] + ": " + r["prompt"]).replace("|", "/")[:120], "auto": True}
        old = next((x for x in doc["entries"] if x.get("sid") == e["sid"]), None)
        if old and old.get("tokens") == e["tokens"]:
            continue
        if old:
            e["purpose"] = old.get("purpose", e["purpose"])  # keep a purpose the person corrected
            e["note"] = old.get("note", e["note"])
        doc["entries"] = [x for x in doc["entries"] if x.get("sid") != e["sid"]] + [e]
        changed[m] = changed.get(m, 0) + 1
    out = os.path.join(root, "merged")
    os.makedirs(out, exist_ok=True)
    for m, n in sorted(changed.items()):
        with open(os.path.join(out, m + ".json"), "w", encoding="utf-8") as fh:
            json.dump({"entries": docs[m]["entries"]}, fh, ensure_ascii=False)
        print(f"{m}: {n} session(s) added or updated -> {os.path.join(out, m + '.json')} (if_version: {docs[m]['version'] or 'lấy version của tài liệu này từ kết quả list; bỏ trống nếu tháng mới'})")
    if not changed:
        print("Nothing new to sync.")


if __name__ == "__main__":
    main()
