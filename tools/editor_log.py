"""Editors' log: every update and correction noted in the posts (the `updates:` field), newest first.
For the editorial team only; it is not part of the website.

    python3 tools/editor_log.py            # all notes
    python3 tools/editor_log.py تصحيح      # only notes containing a word
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
word = sys.argv[1] if len(sys.argv) > 1 else ""
rows = []
for f in glob.glob(os.path.join(ROOT, "content", "posts", "*.md")):
    text = open(f, encoding="utf-8").read()
    head = text.split("\n---", 1)[0]
    title = (re.search(r"^title:\s*(.+)$", head, re.M) or [None, ""])[1].strip().strip("\"'")
    up = re.search(r"^updated:\s*(.+)$", head, re.M)
    if up:
        un = (re.search(r"^update_note:\s*(.+)$", head, re.M) or [None, "تحديث"])[1]
        if word in un:
            rows.append((up[1].strip().strip("\"'"), title, un.strip().strip("\"'"), os.path.basename(f)))
    block = re.search(r"^updates:\s*\n((?:\s+-.*\n?)+)", head, re.M)
    for line in (block[1].splitlines() if block else []):
        d, _, note = line.strip().lstrip("-").strip().strip("\"'").partition("|")
        if word in note:
            rows.append((d.strip(), title, note.strip(), os.path.basename(f)))
for d, title, note, f in sorted(rows, reverse=True):
    print(f"{d}  {title}\n    {note}\n    ({f})\n")
print(f"{len(rows)} ملاحظة")
