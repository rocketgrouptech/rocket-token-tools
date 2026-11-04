#!/usr/bin/env python3
"""Score every recent Claude Code session automatically, from the local session logs.

Reads ~/.claude/projects/**/*.jsonl and rebuilds each session's working pattern
(messages sent, corrections, images, model, web use, reply length, task type).

Two kinds of numbers come out, and only the second one is judged:
- volume: the pattern score (score.py) and the output tokens. A bigger task is
  allowed to be bigger; volume is shown, never ranked.
- efficiency: `ratio` = tokens Claude had to read per token it produced, from the
  measured usage (cache reads weighted at 0.1, as they cost about a tenth), and
  `fix` / `turns`. These do not grow with task size, so this week can be compared
  fairly with last week.

Usage:
  python3 cc_patterns.py --days 14              # table + TP1 codes
  python3 cc_patterns.py --days 14 --sync DIR   # merge into the lesson's log docs saved in DIR
                                                # (read with ArtifactData out_dir); writes DIR/merged/<doc>.json
"""
import argparse
import glob
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import estimate  # noqa: E402

TASK_HINTS = [  # first match wins
    ("slides", r"slide|pptx|deck|thuyết trình|trình chiếu"),
    ("media", r"video|reel|render|recap|hyperframes|thumbnail|voice|tts|ảnh"),
    ("docs", r"docx|\bdoc\b|báo cáo|report|tài liệu|bài giảng|proposal"),
    ("email", r"email|e-mail|\bthư\b|reply|caption"),
    ("excel", r"csv|excel|xlsx|dữ liệu|dashboard|chart|biểu đồ|sql"),
    ("research", r"research|tìm hiểu|nghiên cứu|so sánh"),
]
FIX = re.compile(r"(không phải|sai rồi|chưa đúng|làm lại|sửa lại|vẫn (còn )?lỗi|ý tôi là|ý mình là|"
                 r"^no[,. ]|wrong|that's not|not what i|try again|still (broken|wrong|failing)|doesn'?t work)", re.I)


def prompt_text(content):
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        content = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return (content or "").strip()


def images(content):
    return sum(1 for b in content if isinstance(b, dict) and b.get("type") == "image") if isinstance(content, list) else 0


def scan(root, days):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    S, seen = {}, set()
    for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
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
                if not ts or not sid or d.get("isSidechain"):
                    continue
                t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if t < since:
                    continue
                s = S.setdefault(sid, {"start": t, "project": "", "first": "", "turns": 0, "fix": 0, "img": 0,
                                       "docs": 0, "out": 0, "read": 0, "web": 0, "models": {}})
                s["start"] = min(s["start"], t)
                if not s["project"] and d.get("cwd"):
                    s["project"] = os.path.basename(d["cwd"])
                msg = d.get("message") or {}
                if d.get("type") == "user" and not d.get("isMeta") and not d.get("isCompactSummary"):
                    c = msg.get("content")
                    txt = prompt_text(c)
                    if txt is None or txt.startswith("Base directory for this skill") or txt.startswith("<local-command") \
                            or txt.startswith("<system-reminder>") \
                            or txt.startswith("<scheduled-task"):
                        if txt and txt.startswith("<scheduled-task") and not s["first"]:
                            s["first"] = "scheduled task " + (re.findall(r'name="([^"]+)"', txt) or [""])[0]
                        continue
                    s["turns"] += 1
                    s["img"] += images(c)
                    s["docs"] += sum(1 for b in c if isinstance(b, dict) and b.get("type") == "document") if isinstance(c, list) else 0
                    if s["turns"] > 1 and FIX.search(txt[:300]):
                        s["fix"] += 1
                    if not s["first"]:
                        m = re.search(r"<command-name>/?([^<]+)</command-name>", txt)
                        s["first"] = ("/" + m.group(1).strip()) if m else re.sub(r"\s+", " ", txt)[:100]
                u = msg.get("usage")
                if d.get("type") == "assistant":
                    for b in msg.get("content") or []:
                        if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in ("WebSearch", "WebFetch"):
                            s["web"] = 1
                    key = msg.get("id") or d.get("uuid")
                    if u and key not in seen:
                        seen.add(key)
                        s["out"] += u.get("output_tokens", 0)
                        s["read"] += (u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                                      + 0.1 * u.get("cache_read_input_tokens", 0))
                        if (u.get("server_tool_use") or {}).get("web_search_requests"):
                            s["web"] = 1
                        mdl = msg.get("model") or ""
                        s["models"][mdl] = s["models"].get(mdl, 0) + u.get("output_tokens", 0)
    return S


def to_pattern(sid, s):
    top = max(s["models"], key=s["models"].get) if s["models"] else ""
    model = "nhe" if "haiku" in top else "vua" if "sonnet" in top else "manh"
    per = s["out"] / max(1, s["turns"])
    length = "ngan" if per < 500 else "vua" if per < 2000 else "dai"
    text = (s["first"] + " " + s["project"]).lower()
    task = next((code for code, pat in TASK_HINTS if re.search(pat, text)), "code")
    p = {"task": task, "turns": max(1, s["turns"]), "fix": s["fix"], "pages": s["docs"] * 5, "img": s["img"],
         "len": length, "model": model, "web": s["web"], "old": 0}
    score, _ = estimate(p)
    p.update({"out": s["out"], "read": int(s["read"]), "ratio": round(s["read"] / max(1, s["out"]), 1),
              "id": "cc-" + sid, "sid": sid, "date": s["start"].astimezone().strftime("%Y-%m-%d"), "score": score,
              "auto": True, "env": "code", "note": (s["project"] + ": " + s["first"]).replace("|", "/")[:120],
              "createdAt": int(time.time() * 1000)})
    return p


def code_of(p):
    return "TP1|date={date}|task={task}|turns={turns}|fix={fix}|pages={pages}|img={img}|len={len}|model={model}|web={web}|old=0".format(**p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--sync", metavar="DIR")
    ap.add_argument("--root", default=os.path.expanduser("~/.claude/projects"))
    a = ap.parse_args()
    rows = [to_pattern(sid, s) for sid, s in scan(a.root, a.days).items() if s["turns"] or s["out"]]
    rows.sort(key=lambda r: r["date"])

    if not a.sync:
        print(f"{len(rows)} Claude Code sessions in the last {a.days} days\n")
        for r in rows:
            print(f"{r['date']}  {r['task']:<8} {r['turns']:>3} msgs {r['fix']:>2} fixes  out {r['out']:>8}  ratio {r['ratio']:>5}  {r['note'][:50]}")
            print("  " + code_of(r))
        return

    have = {}
    for path in glob.glob(os.path.join(a.sync, "**", "*.json"), recursive=True):
        if "merged" in path.split(os.sep) or not os.path.basename(path).startswith("cc-"):
            continue
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        if not isinstance(d, dict):
            continue
        have[os.path.basename(path)[:-5]] = d.get("data") if isinstance(d.get("data"), dict) else d
    out = os.path.join(a.sync, "merged")
    os.makedirs(out, exist_ok=True)
    n = 0
    for r in rows:
        old = have.get(r["id"])
        if old and old.get("turns") == r["turns"] and old.get("out") == r["out"]:
            continue
        if old:  # keep a task type or date the person corrected on the page
            r["task"] = old.get("task", r["task"])
            r["createdAt"] = old.get("createdAt", r["createdAt"])
            r["score"], _ = estimate(r)
        with open(os.path.join(out, r["id"] + ".json"), "w", encoding="utf-8") as fh:
            json.dump({k: v for k, v in r.items() if k != "id"}, fh, ensure_ascii=False)
        print(f"{'update' if old else 'new   '} {r['id']}  {r['date']} {r['task']} {r['score']} pts")
        n += 1
    print(f"{n} session(s) to write from {out}" if n else "Nothing new to sync.")
    # keep the shared store small: auto rows older than 60 days are no longer compared on the page
    cutoff = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    stale = sorted(k for k, v in have.items() if k.startswith("cc-") and v.get("auto") and v.get("date", "9999") < cutoff)
    with open(os.path.join(a.sync, "stale.txt"), "w") as fh:
        fh.write("\n".join(stale))
    if stale:
        print(f"{len(stale)} auto row(s) older than 60 days to delete, ids in {os.path.join(a.sync, 'stale.txt')}")


if __name__ == "__main__":
    main()
