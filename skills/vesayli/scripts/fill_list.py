#!/usr/bin/env python3
"""Render a weekly pill box fill list from a small JSON meds file.

The fill list is the weekly ritual: one bottle at a time. Per-slot pill
counts times active days equals the pills needed for the week. Stock
warnings come first, so nothing gets filled blind.

Meds file shape (a JSON list):
  [{"name": "Vitamin D", "count": 2, "form": "softgels",
    "slot": "morning", "until": "2026-10-25", "status": "taking"}]
Fields: name (string), count (pills per slot), form (string),
slot (morning, midday or evening), until (YYYY-MM-DD or null),
status (taking, low or out).

Local only. No network calls.

Usage:
  fill_list.py meds.json [--week YYYY-MM-DD] [--out fill.md]
  --week sets the Monday the week starts on. Defaults to this week.
  Prints markdown to stdout when --out is not given.

Exit 0 always. A missing, malformed, or empty file renders an honest
empty message, never an error.
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta

SLOT_ORDER = ["morning", "midday", "evening"]
SLOT_RULES = {
    "morning": "before food",
    "midday": "after the first meal",
    "evening": "after dinner",
}
SLOT_TITLES = {
    "morning": "Morning",
    "midday": "Midday",
    "evening": "Evening",
}
LOW_LABEL = "low, check you have enough"
OUT_LABEL = "out, leave it out until it arrives"


def monday_of(day):
    return day - timedelta(days=day.weekday())


def fmt_day(day):
    return "%d %s %d" % (day.day, day.strftime("%b"), day.year)


def parse_meds(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    return data


def active_days(item, week):
    until = item.get("until")
    end = None
    if until:
        try:
            end = date.fromisoformat(str(until))
        except ValueError:
            end = None
    return [d for d in week if end is None or d <= end]


def render_fill(meds, week_start):
    week = [week_start + timedelta(days=i) for i in range(7)]
    lines = []
    lines.append("# Pill box fill list")
    lines.append("")
    if not meds:
        lines.append("No meds in the fill list. "
                     "Add items to the JSON file and run again.")
        lines.append("")
        return "\n".join(lines)
    lines.append("Week of %s to %s." % (week[0].isoformat(), week[6].isoformat()))
    lines.append("")

    warnings = []
    for item in meds:
        status = str(item.get("status") or "taking").lower()
        name = str(item.get("name") or "Unnamed").strip()
        if status == "low":
            warnings.append("- %s: %s" % (name, LOW_LABEL))
        elif status == "out":
            warnings.append("- %s: %s" % (name, OUT_LABEL))
    lines.append("## Before you fill")
    lines.append("")
    if warnings:
        lines.extend(warnings)
    else:
        lines.append("- Stock looks fine. Nothing low or out.")
    lines.append("")

    for slot in SLOT_ORDER:
        lines.append("## %s: %s" % (SLOT_TITLES[slot], SLOT_RULES[slot]))
        lines.append("")
        shown = False
        for item in meds:
            if str(item.get("slot") or "").lower() != slot:
                continue
            status = str(item.get("status") or "taking").lower()
            if status == "out":
                continue
            name = str(item.get("name") or "Unnamed").strip()
            form = str(item.get("form") or "").strip()
            try:
                count = int(item.get("count") or 0)
            except (TypeError, ValueError):
                count = 0
            days = active_days(item, week)
            if not days:
                continue
            label = name
            if form:
                label = "%s (%d %s)" % (name, count, form)
            total = count * len(days)
            note = ""
            until = item.get("until")
            if until:
                try:
                    note = ", until %s" % fmt_day(date.fromisoformat(str(until)))
                except ValueError:
                    note = ""
            lines.append("- %s: %d x %d days = %d total%s"
                         % (label, count, len(days), total, note))
            shown = True
        if not shown:
            lines.append("- (nothing scheduled)")
        lines.append("")

    unscheduled = [i for i in meds
                   if str(i.get("slot") or "").lower() not in SLOT_ORDER
                   and str(i.get("status") or "taking").lower() != "out"]
    if unscheduled:
        lines.append("## Unscheduled")
        lines.append("")
        for item in unscheduled:
            lines.append("- %s: no slot set, fill by hand"
                         % str(item.get("name") or "Unnamed").strip())
        lines.append("")

    resting = []
    for item in meds:
        days = active_days(item, week)
        if not days:
            until = item.get("until")
            stamp = ""
            if until:
                try:
                    stamp = " (ended %s)" % fmt_day(date.fromisoformat(str(until)))
                except ValueError:
                    stamp = ""
            resting.append("- %s%s" % (str(item.get("name") or "Unnamed").strip(), stamp))
    if resting:
        lines.append("## Not this week")
        lines.append("")
        lines.extend(resting)
        lines.append("")

    lines.append("Fill one bottle at a time. Tick each with who and when. "
                 "Then do the check pass, slot by slot.")
    lines.append("")
    return "\n".join(lines)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("meds", nargs="?", default=None)
    parser.add_argument("--week", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    if args.week:
        try:
            week_start = monday_of(date.fromisoformat(args.week))
        except ValueError:
            week_start = monday_of(date.today())
    else:
        week_start = monday_of(date.today())
    meds = parse_meds(args.meds) if args.meds else None
    out = render_fill(meds, week_start)
    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(out)
        except OSError:
            sys.stdout.write(out)
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main(sys.argv[1:])
