#!/usr/bin/env python3
"""Render a styled, printable doctor summary from VeSayLi daily logs.

Same data as one_pager.py, presented as a single self-contained HTML file:
readable on a phone, clean when printed for the doctor. Inline CSS, no
external assets, no network calls.

Usage:
  one_pager_html.py <logdir> [--days 7] [--out summary.html]
  Prints the HTML to stdout when --out is not given.
"""
import argparse
import html
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import one_pager  # noqa: E402


CSS = """
body { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
       color: #1a1a1a; max-width: 640px; margin: 0 auto; padding: 24px 20px;
       line-height: 1.5; }
header { border-bottom: 3px solid #1a1a1a; padding-bottom: 12px;
         margin-bottom: 24px; }
header h1 { font-size: 24px; margin: 0 0 4px 0; }
header p { color: #555; margin: 0; font-size: 14px; }
h2 { font-size: 16px; text-transform: uppercase; letter-spacing: 1px;
     color: #444; margin: 28px 0 12px 0; }
.med { margin: 0 0 14px 0; }
.med .name { font-weight: 600; }
.med .bar { height: 8px; background: #e8e8e8; border-radius: 4px;
            margin-top: 6px; overflow: hidden; }
.med .fill { height: 100%; background: #2a7a4b; border-radius: 4px; }
.med .stat { font-size: 13px; color: #555; margin-top: 4px; }
.entry { margin: 0 0 10px 0; }
.entry .day { font-weight: 600; }
.qline { border-bottom: 1px solid #ccc; height: 28px; }
footer { margin-top: 32px; padding-top: 12px; border-top: 1px solid #ccc;
         font-size: 13px; color: #666; }
@media print {
  body { padding: 0; max-width: none; }
  .med .fill { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
"""


def pct(hit, total):
    if total <= 0:
        return 0
    return int(round(100.0 * hit / total))


def render_html(logdir, days):
    logs = one_pager.read_daily_logs(logdir, days)
    today = date.today().isoformat()
    parts = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html><head><meta charset=\"utf-8\">")
    parts.append("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">")
    parts.append("<title>Doctor visit summary</title>")
    parts.append("<style>%s</style></head><body>" % CSS)
    parts.append("<header><h1>Doctor visit summary</h1>")
    if logs:
        parts.append("<p>Generated %s from your daily logs. Last %d days.</p>"
                     % (today, days))
    else:
        parts.append("<p>Generated %s. No daily logs found in the last %d days.</p>"
                     % (today, days))
    parts.append("</header>")

    parts.append("<h2>Medications</h2>")
    meds = one_pager.med_summary(logs)
    if meds:
        for _key, shown, hit, total in meds:
            if total == 1:
                stat = "taken" if hit else "not taken"
            else:
                stat = "taken %d of %d days" % (hit, total)
            parts.append("<div class=\"med\"><div class=\"name\">%s</div>"
                         % html.escape(shown))
            parts.append("<div class=\"bar\"><div class=\"fill\" style=\"width:%d%%\">"
                         "</div></div>" % pct(hit, total))
            parts.append("<div class=\"stat\">%s</div></div>" % stat)
    else:
        parts.append("<p>No meds logged in this period.</p>")

    parts.append("<h2>How the days felt</h2>")
    felt_any = False
    for day, sections in logs:
        for line in sections["feels"]:
            text = one_pager.plain_feel(line)
            if text:
                parts.append("<div class=\"entry\"><span class=\"day\">%s:</span> %s</div>"
                             % (html.escape(day), html.escape(text)))
                felt_any = True
    if not felt_any:
        parts.append("<p>Nothing recorded in this period.</p>")

    parts.append("<h2>Notes</h2>")
    notes_any = False
    for day, sections in logs:
        for line in sections["notes"]:
            text = one_pager.plain_feel(line)
            if text:
                parts.append("<div class=\"entry\"><span class=\"day\">%s:</span> %s</div>"
                             % (html.escape(day), html.escape(text)))
                notes_any = True
    if not notes_any:
        parts.append("<p>Nothing recorded in this period.</p>")

    parts.append("<h2>Stopped</h2>")
    seen = []
    for day, sections in logs:
        for line in sections["stopped"]:
            text = one_pager.plain_feel(line)
            if text and text not in seen:
                seen.append(text)
    for text in seen:
        parts.append("<div class=\"entry\">%s</div>" % html.escape(text))
    if not seen:
        parts.append("<p>Nothing stopped in this period.</p>")

    parts.append("<h2>Questions for my doctor</h2>")
    parts.append("<div class=\"qline\"></div>" * 4)

    parts.append("<footer>VeSayLi by Please Romaine Calm. This summary organizes your own notes. "
                 "It is not medical advice.</footer>")
    parts.append("</body></html>")
    return "\n".join(parts)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("logdir")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    out = render_html(args.logdir, args.days)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main(sys.argv[1:])
