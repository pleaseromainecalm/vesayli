#!/usr/bin/env python3
"""File the Day-1 interview: write meds.json and the first daily log.

The interview itself is a conversation, documented in SKILL.md. This
script only files what the user said. Nothing is ever filled in by
guessing.

Answers file shape:
  {"user": "Sam",
   "meds": [{"name": "Vitamin D", "dose": "1000 IU", "count": 1,
             "form": "softgel", "slot": "morning",
             "until": null, "status": "taking"}],
   "stopped": [{"what": "Elderberry", "when": "2026-10-13",
                "why": "bottle finished"}]}

Fields: name, dose (as printed on the log line), count (pills per
slot), form, slot (morning, midday or evening), until (YYYY-MM-DD or
null), status (taking, low or out). The stopped list is optional.

Writes meds.json in the fill_list.py schema and log-<today>.md in the
SKILL.md daily log shape, with unchecked boxes, the user's dose and
status words, and empty feels, notes, and stopped sections.

Local only. No network calls. Creates the output directory if needed.

Usage:
  onboard.py --answers answers.json --out-dir ./start

Exit 0 always. A missing or malformed answers file prints an honest
message and writes nothing.
"""
import argparse
import json
import os
import sys
from datetime import date

SLOT_ORDER = ["morning", "midday", "evening"]
SLOT_TITLES = {
    "morning": "Morning",
    "midday": "Midday",
    "evening": "Evening",
}
SLOT_RULES = {
    "morning": "before food",
    "midday": "after the first meal",
    "evening": "after dinner",
}
STATUS_WORDS = {
    "taking": "taking",
    "low": "low, reordered",
    "out": "out",
}


def load_answers(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("meds"), list):
        return None
    return data


def status_words(status, until):
    words = STATUS_WORDS.get(str(status or "taking").lower(), "taking")
    if until:
        words = words + ", short course until " + str(until)
    return words


def render_meds_json(meds):
    out = []
    for m in meds:
        try:
            count = int(m.get("count") or 0)
        except (TypeError, ValueError):
            count = 0
        out.append({
            "name": str(m.get("name") or "Unnamed").strip(),
            "count": count,
            "form": str(m.get("form") or "").strip(),
            "slot": str(m.get("slot") or "").strip().lower(),
            "until": m.get("until"),
            "status": str(m.get("status") or "taking").strip().lower(),
        })
    return out


def render_log(meds, stopped, today):
    lines = []
    lines.append("# " + today)
    lines.append("")
    lines.append("## Meds and supplements")
    lines.append("")
    for slot in SLOT_ORDER:
        lines.append("### %s: %s" % (SLOT_TITLES[slot], SLOT_RULES[slot]))
        shown = False
        for m in meds:
            if str(m.get("slot") or "").lower() != slot:
                continue
            name = str(m.get("name") or "Unnamed").strip()
            dose = str(m.get("dose") or "").strip()
            label = (name + " " + dose).strip()
            lines.append("- [ ] %s (%s)"
                         % (label, status_words(m.get("status"),
                                                m.get("until"))))
            shown = True
        if not shown:
            lines.append("- [ ] (nothing scheduled)")
        lines.append("")
    lines.append("## How today feels")
    lines.append("- (the user's own words go here)")
    lines.append("")
    lines.append("## Notes")
    lines.append("- Started with the Day-1 interview.")
    lines.append("")
    lines.append("## Stopped")
    if stopped:
        for s in stopped:
            if not isinstance(s, dict):
                continue
            what = str(s.get("what") or "").strip()
            when = str(s.get("when") or "").strip()
            why = str(s.get("why") or "").strip()
            if what:
                lines.append("- %s, stopped %s, %s" % (what, when, why))
    else:
        lines.append("- (what stopped, when, why. A new doctor needs this "
                     "more than the current list.)")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(
        description="VeSayLi Day-1 onboarding: file the interview answers")
    parser.add_argument("--answers", required=True,
                        help="JSON answers file from the interview")
    parser.add_argument("--out-dir", required=True,
                        help="directory to write meds.json and the first log")
    args = parser.parse_args(argv)
    data = load_answers(args.answers)
    if data is None:
        print("Could not read the answers file. Nothing was written.")
        return 0
    try:
        os.makedirs(args.out_dir, exist_ok=True)
    except OSError:
        print("Could not create the output directory. Nothing was written.")
        return 0
    meds = data["meds"]
    stopped = data.get("stopped") or []
    today = date.today().isoformat()
    meds_path = os.path.join(args.out_dir, "meds.json")
    log_path = os.path.join(args.out_dir, "log-%s.md" % today)
    try:
        with open(meds_path, "w", encoding="utf-8") as f:
            json.dump(render_meds_json(meds), f, indent=2)
            f.write("\n")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(render_log(meds, stopped, today))
    except OSError:
        print("Could not write the output files. Nothing was filed.")
        return 0
    print("Wrote %s" % meds_path)
    print("Wrote %s" % log_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
