#!/usr/bin/env python3
"""Pattern-based token score for one Claude chat session.

This is a relative estimate for comparing how the same kind of task was done
week over week. It is NOT a real token count. The formula matches the
"Nhật ký tiết kiệm" tracker in the Token lesson page; keep them in sync.

Usage:
  python3 score.py "TP1|task=slides|turns=6|fix=2|pages=5|img=3|len=dai|model=vua|web=0|old=0"
  python3 score.py "<this week's code>" "<last week's code>"   # compare two sessions
"""
import math
import sys

TASKS = {  # A = Claude's visible reply per turn, T = hidden code/tool work per turn
    "qa": ("Hỏi đáp nhanh", 300, 0),
    "email": ("Viết email, văn bản ngắn", 500, 0),
    "summary": ("Tóm tắt tài liệu", 800, 0),
    "docs": ("Tạo file Docs / Word", 1500, 3000),
    "excel": ("Phân tích Excel, dữ liệu", 1000, 5000),
    "slides": ("Tạo slides", 2500, 8000),
    "research": ("Nghiên cứu web sâu", 2000, 40000),
    "code": ("Lập trình, Claude Code", 1500, 6000),
    "media": ("Video, ảnh, giọng đọc", 1500, 6000),
}
LEN = {"ngan": 0.5, "vua": 1.0, "dai": 2.0}
MODEL = {"nhe": 0.35, "vua": 1.0, "manh": 1.7}
INT_KEYS = ("turns", "fix", "pages", "img", "web", "old")


def parse(code):
    parts = code.strip().split("|")
    if parts[0] != "TP1":
        raise ValueError("Code must start with TP1|")
    p = {"task": "qa", "turns": 1, "fix": 0, "pages": 0, "img": 0, "len": "vua", "model": "vua", "web": 0, "old": 0}
    for seg in parts[1:]:
        if "=" in seg:
            k, v = seg.split("=", 1)
            p[k.strip()] = v.strip()
    for k in INT_KEYS:
        p[k] = max(0, int(p[k]))
    p["turns"] = max(1, p["turns"])
    if p["task"] not in TASKS or p["len"] not in LEN or p["model"] not in MODEL:
        raise ValueError("Unknown task/len/model value in: " + code)
    return p


def estimate(p):
    _, a, t = TASKS[p["task"]]
    n = p["turns"]
    tri = n * (n + 1) / 2
    w = MODEL[p["model"]]
    web = 4000 if p["web"] and p["task"] != "research" else 0
    parts = {
        "Lịch sử cũ mang theo": n * p["old"] * 900 * w,
        "File đính kèm": n * (p["pages"] * 1500 + p["img"] * 1600) * w,
        "Tin của bạn": 200 * tri * w,
        "Trả lời của Claude": a * LEN[p["len"]] * tri * w,
        "Code, công cụ, ảnh kiểm tra": (t + web) * tri * w,
    }
    score = math.floor(sum(parts.values()) / 100 + 0.5) / 10
    return score, parts


def report(code):
    p = parse(code)
    score, parts = estimate(p)
    total = sum(parts.values()) or 1
    print(f"{TASKS[p['task']][0]}: {score} điểm token (ước lượng tương đối)")
    for name, v in sorted(parts.items(), key=lambda x: -x[1]):
        if v:
            print(f"  - {name}: {round(v / total * 100)}%")
    return p, score


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    p1, s1 = report(sys.argv[1])
    if len(sys.argv) > 2:
        print()
        p0, s0 = report(sys.argv[2])
        if p0["task"] != p1["task"]:
            print("\nLưu ý: hai phiên khác loại việc, so sánh chỉ mang tính tham khảo.")
        pct = round((s1 - s0) / s0 * 100) if s0 else 0
        print(f"\nSo với phiên trước: {'tiết kiệm ' + str(-pct) if pct <= 0 else 'tốn hơn ' + str(pct)}%")
        for k in ("turns", "fix", "pages", "img", "old"):
            if p0[k] != p1[k]:
                print(f"  - {k}: {p0[k]} → {p1[k]}")
