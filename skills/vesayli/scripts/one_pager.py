#!/usr/bin/env python3
"""Render a doctor one-pager from VeSayLi daily logs.

This is the flagship output of the companion: visible, readable, and the
user's own. It reads a folder of daily markdown logs (one file per day,
named log-YYYY-MM-DD.md, in the shape SKILL.md defines) and renders a
weekly doctor summary with headings and plain words.

Local only. No network calls. Reads the log folder, writes markdown.

Usage:
  one_pager.py <logdir> [--days 7] [--out visit.md]
  Prints markdown to stdout when --out is not given.

Exit 0 always. A missing or empty log folder renders an honest empty
summary, never an error.
"""
import argparse
import os
import re
import sys
from datetime import date, timedelta

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
CHECK_RE = re.compile(r"^-\s*\[(x| )\]\s*(.+)$", re.I)
BULLET_RE = re.compile(r"^-\s+(.+)$")

SECTIONS = {
    "meds": "meds and supplements",
    "feels": "how today feels",
    "notes": "notes",
    "stopped": "stopped",
}


def read_daily_logs(logdir, days):
    """Return a list of (date_str, sections) for the last N days."""
    try:
        names = os.listdir(logdir)
    except OSError:
        return []
    cutoff = date.today() - timedelta(days=days - 1)
    found = []
    for name in names:
        m = DATE_RE.search(name)
        if not m:
            continue
        try:
            day = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if day < cutoff:
            continue
        path = os.path.join(logdir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        found.append((m.group(1), parse_sections(text)))
    found.sort()
    return found


def parse_sections(text):
    """Split a daily log into its sections as bullet lists.

    Only ## level headings start a new section. ### subheadings
    (time slots inside the meds section) keep the current section."""
    sections = {key: [] for key in SECTIONS}
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            if stripped.startswith("###"):
                continue
            head = stripped.lstrip("#").strip().lower()
            current = None
            for key, label in SECTIONS.items():
                if label in head:
                    current = key
                    break
            continue
        if current and stripped.startswith("-"):
            sections[current].append(stripped)
    return sections


def split_med(line):
    """Split a med bullet into (label, taken)."""
    m = CHECK_RE.match(line)
    if m:
        return m.group(2).strip(), m.group(1).lower() == "x"
    m = BULLET_RE.match(line)
    if m:
        return m.group(1).strip(), None
    return line.strip(), None


def base_med(label):
    """Group key for a med label. Strip parenthetical notes and dose
    quantities so a dose change merges with the earlier line instead
    of stacking as a separate med."""
    text = re.sub(r"\s*\(.*?\)\s*", " ", label)
    text = re.sub(r"\b\d+(?:\.\d+)?\s*(tablets?|capsules?|pills?|mg|g|mcg|iu|ml|drops?)\b",
                  " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip().lower()


def plain_feel(line):
    m = BULLET_RE.match(line)
    return m.group(1).strip() if m else line.strip()


def plural(n, word):
    if n == 1:
        return "%d %s" % (n, word)
    return "%d %ss" % (n, word)


def med_summary(logs):
    """Aggregate med adherence across daily logs.

    Returns a sorted list of (key, display label, days taken, days
    logged). A dose change merges into one line showing the latest
    wording."""
    med_stats = {}
    for _day, sections in logs:
        seen_today = set()
        for line in sections["meds"]:
            label, taken = split_med(line)
            key = base_med(label)
            if not label or key in seen_today:
                continue
            seen_today.add(key)
            total, hit, _shown = med_stats.get(key, (0, 0, label))
            total += 1
            if taken:
                hit += 1
            med_stats[key] = (total, hit, label)
    return [(key, shown, hit, total)
            for key, (total, hit, shown) in sorted(med_stats.items())]


def render(logdir, days):
    logs = read_daily_logs(logdir, days)
    lines = []
    lines.append("# Doctor visit one-pager")
    lines.append("")
    if logs:
        lines.append("Generated %s from your daily logs. Last %d days."
                     % (date.today().isoformat(), days))
    else:
        lines.append("Generated %s. No daily logs found in the last %d days."
                     % (date.today().isoformat(), days))
    lines.append("")

    lines.append("## Medications")
    lines.append("")
    for _key, shown, hit, total in med_summary(logs):
        lines.append("- %s: taken %s"
                     % (shown, plural(hit, "day") if total == 1
                        else "%d of %d days" % (hit, total)))
    if not med_summary(logs):
        lines.append("- No meds logged in this period.")
    lines.append("")

    lines.append("## How the days felt")
    lines.append("")
    felt_any = False
    for day, sections in logs:
        for line in sections["feels"]:
            text = plain_feel(line)
            if text:
                lines.append("- %s: %s" % (day, text))
                felt_any = True
    if not felt_any:
        lines.append("- Nothing recorded in this period.")
    lines.append("")

    lines.append("## Notes")
    lines.append("")
    notes_any = False
    for day, sections in logs:
        for line in sections["notes"]:
            text = plain_feel(line)
            if text:
                lines.append("- %s: %s" % (day, text))
                notes_any = True
    if not notes_any:
        lines.append("- Nothing recorded in this period.")
    lines.append("")

    lines.append("## Stopped")
    lines.append("")
    seen = []
    for day, sections in logs:
        for line in sections["stopped"]:
            text = plain_feel(line)
            if text and text not in seen:
                seen.append(text)
    for text in seen:
        lines.append("- %s" % text)
    if not seen:
        lines.append("- Nothing stopped in this period.")
    lines.append("")

    lines.append("## Questions for my doctor")
    lines.append("")
    lines.append("- (write your questions here before the visit)")
    lines.append("")
    lines.append("VeSayLi by Please Romaine Calm. This summary organizes your own "
                 "notes. It is not medical advice.")
    return "\n".join(lines) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(
        description="VeSayLi doctor one-pager from daily logs")
    parser.add_argument("logdir", help="folder of daily log markdown files")
    parser.add_argument("--days", type=int, default=7,
                        help="lookback window in days")
    parser.add_argument("--out", help="write markdown to this file")
    args = parser.parse_args(argv)
    text = render(args.logdir, args.days)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
