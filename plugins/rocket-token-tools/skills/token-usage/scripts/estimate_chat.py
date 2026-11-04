#!/usr/bin/env python3
"""Rough token estimate for one chat in Claude on the web, desktop or mobile.

Those apps do not show per-chat token counts, so this rebuilds an estimate from
what is visible: characters per turn, attachments and tool output. Every turn
re-reads the whole conversation, which is why long chats grow fast. The hidden
system prompt and tool definitions are not included, and prompt caching makes the
real cost of re-reading lower, so treat the result as an order of magnitude.

Usage:
  python3 estimate_chat.py --turns "300:1800,120:2500,80:900" --lang vi --pages 12 --images 2 --tool-tokens 6000
    --turns  user_chars:reply_chars for each turn, in order
"""
import argparse

CHARS_PER_TOKEN = {"en": 4.0, "vi": 2.5, "mix": 3.2, "code": 3.5}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", required=True)
    ap.add_argument("--lang", default="vi", choices=sorted(CHARS_PER_TOKEN))
    ap.add_argument("--pages", type=int, default=0, help="PDF/document pages attached")
    ap.add_argument("--images", type=int, default=0)
    ap.add_argument("--tool-tokens", type=int, default=0, help="web results, code output, file generation, per chat")
    a = ap.parse_args()

    ratio = CHARS_PER_TOKEN[a.lang]
    turns = []
    for pair in a.turns.split(","):
        u, r = pair.split(":")
        turns.append((int(u) / ratio, int(r) / ratio))
    attach = a.pages * 2000 + a.images * 1600
    tool_per_turn = a.tool_tokens / max(1, len(turns))

    history, total_in, total_out = 0.0, 0.0, 0.0
    for u, r in turns:
        total_in += attach + history + u
        total_out += r + tool_per_turn
        history += u + r + tool_per_turn
    total = int(round(total_in + total_out, -2))
    print(f"Turns: {len(turns)} · input re-read: {int(total_in):,} · output: {int(total_out):,}")
    print(f"Estimated tokens: {total:,}")
    print(f"TOKENS={total}")


if __name__ == "__main__":
    main()
