#!/usr/bin/env python3
"""Read the refill picture aloud from a VeSayLi meds file and logs.

Reports every item with status low or out, how many consecutive recent
log days it was flagged, and a one-line nudge in plain words. Out items
are noted as excluded from fill counts. The tone is conversational: the
companion can read this straight to the user.

Honest about limits: this tracks what the user reported. It does not
know how many pills are left unless the user says so.

Local only. No network calls.

Usage:
  refill_watch.py <meds.json> [<logdir>] [--out refill.md]
  Prints markdown to stdout when --out is not given.

Exit 0 always. A missing or malformed meds file renders an honest
message, never an error.
"""
import argparse
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import one_pager  # noqa: E402
import fill_list  # noqa: E402


def flagged_in_line(line):
    low = line.lower()
    return ("(low" in low) or ("(out" in low) or ("reorder" in low)


def streak(logs, key):
    """Consecutive recent logs where this med was flagged low or out."""
    count = 0
    for _day, sections in reversed(logs):
        hit = False
        for line in sections["meds"]:
            label, _taken = one_pager.split_med(line)
            if one_pager.base_med(label) == key and flagged_in_line(line):
                hit = True
                break
        if hit:
            count += 1
        else:
            break
    return count


def render(meds_path, logdir):
    meds = fill_list.parse_meds(meds_path)
    lines = []
    lines.append("# Refill watch")
    lines.append("")
    lines.append("Generated %s." % date.today().isoformat())
    lines.append("")
    if not meds:
        lines.append("No meds file to read. Add items and run again.")
        lines.append("")
        return "\n".join(lines) + "\n"
    logs = one_pager.read_daily_logs(logdir, 30) if logdir else []
    low = [m for m in meds if str(m.get("status") or "").lower() == "low"]
    out = [m for m in meds if str(m.get("status") or "").lower() == "out"]
    if not low and not out:
        lines.append("Nothing is running low or out. Stock looks fine.")
        lines.append("")
        return "\n".join(lines) + "\n"
    if low:
        lines.append("## Running low")
        lines.append("")
        for item in low:
            name = str(item.get("name") or "Unnamed").strip()
            n = streak(logs, one_pager.base_med(name)) if logs else 0
            if n:
                lines.append("- %s is running low. Flagged %s in a row. "
                             "Reorder now if you have not."
                             % (name, "1 day" if n == 1 else "%d days" % n))
            else:
                lines.append("- %s is running low in the meds file. "
                             "Reorder now if you have not." % name)
        lines.append("")
    if out:
        lines.append("## Out")
        lines.append("")
        for item in out:
            name = str(item.get("name") or "Unnamed").strip()
            lines.append("- %s is out. It stays out of the fill list "
                         "until it arrives." % name)
        lines.append("")
    lines.append("This tracks what you reported. It does not know how many "
                 "pills are left unless you tell it.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(
        description="VeSayLi refill watch from a meds file and logs")
    parser.add_argument("meds", help="JSON meds file")
    parser.add_argument("logdir", nargs="?", default=None,
                        help="folder of daily log markdown files")
    parser.add_argument("--out", help="write markdown to this file")
    args = parser.parse_args(argv)
    text = render(args.meds, args.logdir)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
