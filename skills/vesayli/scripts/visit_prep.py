#!/usr/bin/env python3
"""Build a visit prep page from VeSayLi daily logs.

Two sections. "Questions in your own words" quotes the user's own
feels lines back as question stubs and lists missed doses as plain
facts. A feels phrase that appears on 2 or more days is surfaced once
with its dates. "Before you go" is a short checklist: the printed
one-pager, bottles for anything low or out, insurance card, and the
questions above.

The page only reflects what the user logged. It never interprets,
diagnoses, or suggests what the doctor will say.

Local only. No network calls. Reads the log folder, writes markdown.

Usage:
  visit_prep.py <logdir> [--days 14] [--out visit-prep.md]
  Prints markdown to stdout when --out is not given.

Exit 0 always. A missing or empty log folder renders an honest empty
page, never an error.
"""
import argparse
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import one_pager  # noqa: E402


def short_day(day_str):
    """Format YYYY-MM-DD as 18 Oct."""
    try:
        day = date.fromisoformat(day_str)
    except ValueError:
        return day_str
    return "%d %s" % (day.day, day.strftime("%b"))


def norm_feel(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def feel_similar(a, b):
    """Near-identical wording: token overlap of 0.75 or more."""
    ta = set(norm_feel(a).split())
    tb = set(norm_feel(b).split())
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) >= 0.75


def usable_feel(text):
    """Skip placeholders and fragments too short to quote."""
    text = text.strip()
    if not text or text.startswith("("):
        return False
    if "go here" in text.lower():
        return False
    return len(norm_feel(text).split()) >= 3


def group_feels(feels):
    """Group (day, text) pairs by near-identical wording."""
    groups = []
    for day, text in feels:
        placed = False
        for group in groups:
            if feel_similar(text, group[0][1]):
                group.append((day, text))
                placed = True
                break
        if not placed:
            groups.append([(day, text)])
    return groups


def pick_quote(group):
    """The most common verbatim wording, earliest on a tie."""
    counts = {}
    first = {}
    for day, text in group:
        counts[text] = counts.get(text, 0) + 1
        if text not in first:
            first[text] = day
    top_count = max(counts.values())
    top = [t for t in counts if counts[t] == top_count]
    return min(top, key=lambda t: first[t])


def strip_status(label):
    return re.sub(r"\s*\(.*?\)\s*", "", label).strip()


def missed_doses(logs):
    """List of (label, [days]) for unchecked med lines, in log order.
    Today's log is still in progress, so its unchecked boxes are not
    misses yet."""
    today = date.today().isoformat()
    missed = {}
    order = []
    for day, sections in logs:
        if day == today:
            continue
        for line in sections["meds"]:
            label, taken = one_pager.split_med(line)
            if taken is not False:
                continue
            if not label or label.startswith("("):
                continue
            if "nothing scheduled" in label.lower():
                continue
            key = one_pager.base_med(label)
            if key not in missed:
                missed[key] = [label, []]
                order.append(key)
            missed[key][0] = label
            if day not in missed[key][1]:
                missed[key][1].append(day)
    return [(missed[k][0], missed[k][1]) for k in order]


def low_out_now(logs):
    """(name, status) flagged low or out in the most recent log."""
    if not logs:
        return []
    _day, sections = logs[-1]
    found = []
    for line in sections["meds"]:
        label, _taken = one_pager.split_med(line)
        low = line.lower()
        if ("(low" in low or "(out" in low) and label:
            name = strip_status(label)
            m = re.search(r"\(([^)]*)\)", label)
            status = m.group(1).strip() if m else ""
            if (name, status) not in found:
                found.append((name, status))
    return found


def render(logdir, days):
    logs = one_pager.read_daily_logs(logdir, days)
    lines = []
    lines.append("# Visit prep")
    lines.append("")
    if logs:
        lines.append("Generated %s from your daily logs. Last %d days."
                     % (date.today().isoformat(), days))
    else:
        lines.append("Generated %s. No daily logs found in the last %d days."
                     % (date.today().isoformat(), days))
    lines.append("")
    lines.append("## Questions in your own words")
    lines.append("")
    lines.append("These come from what you logged. Edit them into your own "
                 "words before the visit.")
    lines.append("")
    feels = []
    for day, sections in logs:
        for line in sections["feels"]:
            text = one_pager.plain_feel(line)
            if usable_feel(text):
                feels.append((day, text))
    shown = False
    for group in group_feels(feels):
        if len(group) < 2:
            continue
        quote = pick_quote(group)
        seen_days = []
        for day, _text in group:
            if day not in seen_days:
                seen_days.append(day)
        dates = ", ".join(short_day(d) for d in seen_days)
        lines.append("- \"%s\" (%s) Is that worth mentioning?"
                     % (quote, dates))
        shown = True
    for label, miss_days in missed_doses(logs):
        name = strip_status(label)
        dates = ", ".join(short_day(d) for d in miss_days)
        lines.append("- Missed: %s on %s." % (name or label, dates))
        shown = True
    if not shown:
        lines.append("- Nothing repeated and nothing missed in this period. "
                     "Still worth a look before you go.")
    if any(day == date.today().isoformat() for day, _s in logs):
        lines.append("- Today is still in progress.")
    lines.append("")
    lines.append("This page repeats what you logged. It does not diagnose "
                 "or interpret anything.")
    lines.append("")
    lines.append("## Before you go")
    lines.append("")
    lines.append("- [ ] Print the one-pager. one_pager_html.py makes a clean copy.")
    bottles = low_out_now(logs)
    if bottles:
        parts = ["%s (%s)" % (n, s) if s else n for n, s in bottles]
        lines.append("- [ ] Bring the bottles for anything low or out: %s."
                     % ", ".join(parts))
    else:
        lines.append("- [ ] Bring the bottles for anything low or out.")
    lines.append("- [ ] Insurance card.")
    lines.append("- [ ] These questions, in your own words.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(
        description="VeSayLi visit prep page from daily logs")
    parser.add_argument("logdir", help="folder of daily log markdown files")
    parser.add_argument("--days", type=int, default=14,
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
