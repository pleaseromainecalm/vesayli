#!/usr/bin/env python3
"""Render a travel pack list from a VeSayLi meds file.

Same meds file shape as fill_list.py. Per-slot groups, count times
trip days plus spare equals what to take. Short courses that end
mid-trip pack for fewer days and say so. Out items are excluded with
a note. Stock warnings come first, so low items get sorted before
the bag is packed.

Local only. No network calls.

Usage:
  pack_list.py <meds.json> --days N [--spare 2] [--week YYYY-MM-DD] [--out pack.md]
  --week sets the first day of the trip. Defaults to today.
  Prints markdown to stdout when --out is not given.

Exit 0 always. A missing, malformed, or empty file renders an honest
empty message, never an error.
"""
import argparse
import os
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fill_list  # noqa: E402


def trip_days(start, n):
    return [start + timedelta(days=i) for i in range(n)]


def active_on(item, days):
    until = item.get("until")
    end = None
    if until:
        try:
            end = date.fromisoformat(str(until))
        except ValueError:
            end = None
    return [d for d in days if end is None or d <= end]


def render_pack(meds, start, days, spare):
    trip = trip_days(start, days)
    lines = []
    lines.append("# Travel pack list")
    lines.append("")
    if not meds:
        lines.append("No meds in the meds file. Add items and run again.")
        lines.append("")
        return "\n".join(lines)
    lines.append("%d days from %s, plus %d spare of each item."
                 % (days, fill_list.fmt_day(start), spare))
    lines.append("")

    warnings = []
    for item in meds:
        status = str(item.get("status") or "taking").lower()
        name = str(item.get("name") or "Unnamed").strip()
        if status == "low":
            warnings.append("- %s: %s before you go."
                            % (name, fill_list.LOW_LABEL))
        elif status == "out":
            warnings.append("- %s: %s, left out of the pack list."
                            % (name, fill_list.OUT_LABEL))
    lines.append("## Before you pack")
    lines.append("")
    if warnings:
        lines.extend(warnings)
    else:
        lines.append("- Stock looks fine. Nothing low or out.")
    lines.append("")

    resting = []
    for slot in fill_list.SLOT_ORDER:
        lines.append("## %s: %s"
                     % (fill_list.SLOT_TITLES[slot],
                        fill_list.SLOT_RULES[slot]))
        lines.append("")
        shown = False
        for item in meds:
            if str(item.get("slot") or "").lower() != slot:
                continue
            if str(item.get("status") or "taking").lower() == "out":
                continue
            name = str(item.get("name") or "Unnamed").strip()
            form = str(item.get("form") or "").strip()
            try:
                count = int(item.get("count") or 0)
            except (TypeError, ValueError):
                count = 0
            active = active_on(item, trip)
            if not active:
                until = item.get("until")
                stamp = ""
                if until:
                    try:
                        stamp = " (ended %s)" % fill_list.fmt_day(
                            date.fromisoformat(str(until)))
                    except ValueError:
                        stamp = ""
                resting.append("- %s%s" % (name, stamp))
                continue
            label = name
            if form:
                label = "%s (%d %s)" % (name, count, form)
            take = count * len(active) + spare
            note = ""
            if len(active) < days:
                until = item.get("until")
                try:
                    end = fill_list.fmt_day(date.fromisoformat(str(until)))
                except (TypeError, ValueError):
                    end = "mid-trip"
                note = ". Short course ends %s, pack for %d %s only." % (
                    end, len(active),
                    "day" if len(active) == 1 else "days")
            lines.append("- %s: %d x %d days + %d spare = %d total%s"
                         % (label, count, len(active), spare, take, note))
            shown = True
        if not shown:
            lines.append("- (nothing to pack)")
        lines.append("")

    if resting:
        lines.append("## Not this trip")
        lines.append("")
        lines.extend(resting)
        lines.append("")

    lines.append("Pack one slot at a time and tick each bottle as it goes "
                 "in the bag.")
    lines.append("")
    return "\n".join(lines)


def main(argv):
    parser = argparse.ArgumentParser(
        description="VeSayLi travel pack list from a meds file")
    parser.add_argument("meds", help="JSON meds file")
    parser.add_argument("--days", type=int, required=True,
                        help="trip length in days")
    parser.add_argument("--spare", type=int, default=2,
                        help="spare pills per item")
    parser.add_argument("--week", default=None,
                        help="first day of the trip, YYYY-MM-DD")
    parser.add_argument("--out", help="write markdown to this file")
    args = parser.parse_args(argv)
    if args.week:
        try:
            start = date.fromisoformat(args.week)
        except ValueError:
            start = date.today()
    else:
        start = date.today()
    meds = fill_list.parse_meds(args.meds)
    text = render_pack(meds, start, args.days, args.spare)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main(sys.argv[1:])
