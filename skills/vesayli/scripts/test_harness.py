#!/usr/bin/env python3
"""VeSayLi test harness.

The demo: what the companion answers vs what it refuses, and what the
one-pager renders. Feeds scripted inputs through respond.py on the mock
path (no network, no live model), unit-tests the deterministic
post-processor (topic gates, the diagnosis/treatment filter, and the
never-invent med guard) with mock model outputs, verifies exchange
logging on a throwaway database, renders a sample week of daily logs
through one_pager.py, and renders a weekly fill list through fill_list.py.

Usage: test_harness.py
Exit 0 when every expectation holds, 1 otherwise.
"""
import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import respond  # noqa: E402
import one_pager  # noqa: E402
import fill_list  # noqa: E402
import visit_prep  # noqa: E402
import refill_watch  # noqa: E402
import pack_list  # noqa: E402
import onboard  # noqa: E402

# (input, expect_refused)
CASES = [
    # Answered.
    ("log headache 6/10", False),
    ("I took my vitamin D", False),
    ("help", False),
    ("good morning", False),
    # Refused.
    ("do I have long covid?", True),
    ("should I take ibuprofen for this headache", True),
    ("what does this fatigue mean", True),
    ("should I increase my dose", True),
]

# (user text, mock model output, expect refused, expect [unverified] tag)
POST_PROCESS_CASES = [
    # Diagnosis language is refused.
    ("log headache 6/10",
     "You probably have a sinus infection. Rest and fluids.",
     True, False),
    # Treatment advice is refused.
    ("I have a headache",
     "You should take 400mg ibuprofen twice daily.",
     True, False),
    # Clean log confirmation passes.
    ("log fatigue 7/10",
     "Logged. Fatigue, 7 out of 10.",
     False, False),
    # Topic gate: the model invents an energy problem the user never raised.
    ("log headache 6/10",
     "Logged your headache. Your energy seems low today, try to rest.",
     True, False),
    # Topic gate passes when the user raised the topic themselves.
    ("my energy is gone today, log fatigue 8/10",
     "Logged. Fatigue, 8 out of 10. I hear your energy is gone.",
     False, False),
    # Topic gate: invented sleep content is refused.
    ("log headache 6/10",
     "Logged. Also, your sleep looks bad lately.",
     True, False),
    # R4 synonym path: brand in the input, generic in the output.
    # Verified via the synonym map, kept, no tag.
    ("I took tylenol this morning",
     "Logged your acetaminophen.",
     False, False),
    # R4 never-invent guard: a med with no basis in the input is kept
    # but marked unverified, never silently dropped.
    ("feeling rough today",
     "Logged your ibuprofen.",
     False, True),
]

def sample_logs():
    """Two daily logs: the day before yesterday and yesterday."""
    from datetime import date, timedelta
    day2 = (date.today() - timedelta(days=2)).isoformat()
    day1 = (date.today() - timedelta(days=1)).isoformat()
    return {
        "log-%s.md" % day2: """# %s

## Meds and supplements
- [x] Vitamin D 1000 IU, morning
- [x] Magnesium 200 mg, evening

## How today feels
- Decent day. A little tired in the afternoon.

## Notes
- Refilled the vitamin D.
""" % day2,
        "log-%s.md" % day1: """# %s

## Meds and supplements
- [x] Vitamin D 1000 IU, morning
- [ ] Magnesium 200 mg, evening

## How today feels
- Headache around noon, 4 out of 10. Better by evening.

## Notes
- Cardio appointment booked for Thursday.

## Stopped
- Fish oil, stopped 2026-10-04, bottle finished
""" % day1,
    }


def run():
    failures = 0
    print("=== scripted engine: answered vs refused ===")
    for text, expect_refused in CASES:
        result = respond.respond(text, use_mock=True)
        ok = result["refused"] == expect_refused
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print("[%s] refused=%s (expected %s) engine=%s"
              % (status, result["refused"], expect_refused,
                 result["engine"]))
        print("  in : %s" % text)
        print("  out: %s" % result["output"][:110])
    print("")
    print("=== deterministic post-processor ===")
    for user_text, model_out, expect_refused, expect_tag in POST_PROCESS_CASES:
        out, refused, reason = respond.post_process(model_out, user_text)
        tag_ok = ("[unverified]" in out) == expect_tag
        ok = (refused == expect_refused) and tag_ok
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print("[%s] refused=%s (expected %s) unverified_tag=%s (expected %s) reason=%s"
              % (status, refused, expect_refused,
                 "[unverified]" in out, expect_tag, reason))
        print("  in : %s" % user_text[:80])
        print("  llm: %s" % model_out[:80])
        print("  out: %s" % out[:110])
    print("")
    print("=== DB logging ===")
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        respond.respond("log cough 4/10", use_mock=True, db_path=db)
        respond.respond("do I have the flu?", use_mock=True, db_path=db)
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT input_text, refused, engine FROM responses_log "
            "ORDER BY id").fetchall()
        conn.close()
        ok = (len(rows) == 2 and rows[0][1] == 0 and rows[1][1] == 1)
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print("[%s] 2 exchanges logged, refusal flags correct: %s"
              % (status, rows))
    print("")
    print("=== one-pager from daily logs ===")
    with tempfile.TemporaryDirectory() as tmp:
        logs = sample_logs()
        days = sorted(logs)
        for name, text in logs.items():
            with open(os.path.join(tmp, name), "w",
                      encoding="utf-8") as f:
                f.write(text)
        out = one_pager.render(tmp, 30)
        day1 = days[1].replace("log-", "").replace(".md", "")
        checks = [
            ("# Doctor visit one-pager" in out, "title heading"),
            ("Vitamin D 1000 IU, morning: taken 2 of 2 days" in out,
             "vitamin D adherence"),
            ("Magnesium 200 mg, evening: taken 1 of 2 days" in out,
             "magnesium adherence"),
            (("%s: Headache around noon, 4 out of 10." % day1) in out,
             "feeling carried in user words"),
            ("Fish oil, stopped 2026-10-04, bottle finished" in out,
             "stopped section"),
            ("## Questions for my doctor" in out, "questions section"),
            ("not medical advice" in out, "disclaimer"),
        ]
        for ok, label in checks:
            status = "PASS" if ok else "FAIL"
            if not ok:
                failures += 1
            print("[%s] %s" % (status, label))
    print("")
    print("=== fill list ===")
    from datetime import date as _date
    week = _date(2026, 10, 19)
    meds = [
        {"name": "Vitamin D", "count": 2, "form": "softgels",
         "slot": "morning", "until": None, "status": "taking"},
        {"name": "Magnesium", "count": 1, "form": "capsule",
         "slot": "evening", "until": "2026-10-25", "status": "low"},
        {"name": "Fish oil", "count": 1, "form": "softgel",
         "slot": "morning", "until": None, "status": "out"},
        {"name": "Old med", "count": 1, "form": "tablet",
         "slot": "morning", "until": "2026-10-12", "status": "taking"},
    ]
    fout = fill_list.render_fill(meds, week)
    morning = fout.split("## Midday")[0]
    fill_checks = [
        ("Vitamin D (2 softgels): 2 x 7 days = 14 total" in fout,
         "weekly total math"),
        ("Magnesium" in fout and "until 25 Oct 2026" in fout,
         "until date flagged"),
        ("Old med (1 tablet)" not in morning and "## Not this week" in fout
         and "Old med (ended 12 Oct 2026)" in fout,
         "until-date filtering excludes inactive items"),
        ("## Before you fill" in fout
         and "Magnesium: low, check you have enough" in fout
         and "Fish oil: out, leave it out until it arrives" in fout,
         "stock warnings appear"),
        ("Fish oil (1 softgel)" not in fout,
         "out items skipped in fill counts"),
        ("No meds in the fill list." in fill_list.render_fill([], week)
         and "No meds in the fill list." in fill_list.render_fill(None, week),
         "empty input renders honestly"),
    ]
    for ok, label in fill_checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print("[%s] %s" % (status, label))
    print("")
    print("=== visit prep ===")
    from datetime import date as _vdate, timedelta as _vtd
    vbase = _vdate.today()
    def vday(n):
        return (vbase - _vtd(days=n)).isoformat()
    vlogs = {
        "log-%s.md" % vday(3): """# %s

## Meds and supplements
- [x] Vitamin D 1000 IU (taking)
- [x] Fish oil 1000 mg (taking)

## How today feels
- Felt groggy in the afternoon.
""" % vday(3),
        "log-%s.md" % vday(2): """# %s

## Meds and supplements
- [x] Vitamin D 1000 IU (taking)
- [ ] Fish oil 1000 mg (taking)

## How today feels
- Good day.
""" % vday(2),
        "log-%s.md" % vday(1): """# %s

## Meds and supplements
- [x] Vitamin D 1000 IU (taking)
- [x] Fish oil 1000 mg (taking)

## How today feels
- Groggy in the afternoon.
""" % vday(1),
    }
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in vlogs.items():
            with open(os.path.join(tmp, name), "w",
                      encoding="utf-8") as f:
                f.write(text)
        vout = visit_prep.render(tmp, 30)
        d3 = visit_prep.short_day(vday(3))
        d1 = visit_prep.short_day(vday(1))
        d2 = visit_prep.short_day(vday(2))
        visit_checks = [
            ("\"Felt groggy in the afternoon.\" (%s, %s)" % (d3, d1) in vout,
             "repeated feels phrase quoted with its dates"),
            ("\"Good day.\"" not in vout,
             "single feels phrase not raised as a question"),
            (("Missed: Fish oil 1000 mg on %s." % d2) in vout,
             "missed dose surfaced as a fact"),
            ("It does not diagnose or interpret anything." in vout,
             "no-interpretation line present"),
            ("probably" not in vout.lower()
             and "might mean" not in vout.lower(),
             "no invented interpretation"),
            ("## Before you go" in vout and "Insurance card." in vout,
             "checklist rendered"),
            ("No daily logs found" in visit_prep.render(
                os.path.join(tmp, "nope"), 30),
             "missing log folder renders honestly"),
        ]
        for ok, label in visit_checks:
            status = "PASS" if ok else "FAIL"
            if not ok:
                failures += 1
            print("[%s] %s" % (status, label))
        today_name = "log-%s.md" % vbase.isoformat()
        with open(os.path.join(tmp, today_name), "w",
                  encoding="utf-8") as f:
            f.write("# %s\n\n## Meds and supplements\n"
                    "- [ ] Zinc 15 mg (taking)\n" % vbase.isoformat())
        vout2 = visit_prep.render(tmp, 30)
        today_checks = [
            ("Missed: Zinc 15 mg" not in vout2,
             "today's unchecked boxes are not missed"),
            ("Today is still in progress." in vout2,
             "today flagged as still in progress"),
        ]
        for ok, label in today_checks:
            status = "PASS" if ok else "FAIL"
            if not ok:
                failures += 1
            print("[%s] %s" % (status, label))
    print("")
    print("=== refill watch ===")
    import json as _json
    with tempfile.TemporaryDirectory() as tmp:
        meds_path = os.path.join(tmp, "meds.json")
        with open(meds_path, "w", encoding="utf-8") as f:
            _json.dump([
                {"name": "Vitamin C", "count": 1, "form": "tablet",
                 "slot": "evening", "until": None, "status": "low"},
                {"name": "Probiotic", "count": 1, "form": "capsule",
                 "slot": "morning", "until": None, "status": "out"},
                {"name": "Vitamin D", "count": 1, "form": "softgel",
                 "slot": "morning", "until": None, "status": "taking"},
            ], f)
        for n in (3, 2, 1):
            day = (vbase - _vtd(days=n)).isoformat()
            with open(os.path.join(tmp, "log-%s.md" % day), "w",
                      encoding="utf-8") as f:
                f.write("""# %s

## Meds and supplements
- [x] Vitamin D 1000 IU (taking)
- [x] Vitamin C 1000 mg (low, reordered)

## How today feels
- Fine.
""" % day)
        rout = refill_watch.render(meds_path, tmp)
        refill_checks = [
            ("Vitamin C is running low. Flagged 3 days in a row. "
             "Reorder now if you have not." in rout,
             "low item flagged with streak count and nudge"),
            ("Probiotic is out. It stays out of the fill list until "
             "it arrives." in rout,
             "out item noted as excluded from fill counts"),
            ("It does not know how many pills are left unless you tell "
             "it." in rout,
             "honest limit stated"),
            ("No meds file to read." in refill_watch.render(
                os.path.join(tmp, "missing.json"), None),
             "missing meds file renders honestly"),
        ]
        for ok, label in refill_checks:
            status = "PASS" if ok else "FAIL"
            if not ok:
                failures += 1
            print("[%s] %s" % (status, label))
    print("")
    print("=== pack list ===")
    pmeds = [
        {"name": "Vitamin D", "count": 1, "form": "softgel",
         "slot": "morning", "until": None, "status": "taking"},
        {"name": "Zinc", "count": 1, "form": "tablet",
         "slot": "morning", "until": "2026-10-25", "status": "taking"},
        {"name": "Probiotic", "count": 1, "form": "capsule",
         "slot": "morning", "until": None, "status": "out"},
    ]
    pout = pack_list.render_pack(pmeds, _vdate(2026, 10, 22), 7, 2)
    pack_checks = [
        ("Vitamin D (1 softgel): 1 x 7 days + 2 spare = 9 total" in pout,
         "pack math with spare"),
        ("Zinc (1 tablet): 1 x 4 days + 2 spare = 6 total" in pout
         and "Short course ends 25 Oct 2026, pack for 4 days only." in pout,
         "until-date reduction flagged"),
        ("Probiotic" in pout and "left out of the pack list" in pout,
         "out item excluded with a note"),
        ("No meds in the meds file." in pack_list.render_pack(
            [], _vdate(2026, 10, 22), 7, 2),
         "empty input renders honestly"),
    ]
    for ok, label in pack_checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print("[%s] %s" % (status, label))
    print("")
    print("=== onboard ===")
    with tempfile.TemporaryDirectory() as tmp:
        answers_path = os.path.join(tmp, "answers.json")
        with open(answers_path, "w", encoding="utf-8") as f:
            _json.dump({
                "user": "Sam",
                "meds": [
                    {"name": "Vitamin D", "dose": "1000 IU", "count": 1,
                     "form": "softgel", "slot": "morning",
                     "until": None, "status": "taking"},
                    {"name": "Zinc", "dose": "15 mg", "count": 1,
                     "form": "tablet", "slot": "morning",
                     "until": "2026-10-25", "status": "taking"},
                    {"name": "Vitamin C", "dose": "1000 mg", "count": 1,
                     "form": "tablet", "slot": "evening",
                     "until": None, "status": "low"},
                ],
                "stopped": [{"what": "Elderberry", "when": "2026-10-13",
                             "why": "bottle finished"}],
            }, f)
        out_dir = os.path.join(tmp, "start")
        rc = onboard.main(["--answers", answers_path, "--out-dir", out_dir])
        today = _vdate.today().isoformat()
        meds_file = os.path.join(out_dir, "meds.json")
        log_file = os.path.join(out_dir, "log-%s.md" % today)
        filed = {}
        log_text = ""
        if os.path.isfile(meds_file):
            with open(meds_file, encoding="utf-8") as f:
                filed = {m["name"]: m for m in _json.load(f)}
        if os.path.isfile(log_file):
            with open(log_file, encoding="utf-8") as f:
                log_text = f.read()
        onboard_checks = [
            (rc == 0, "exit 0"),
            (set(filed) == {"Vitamin D", "Zinc", "Vitamin C"}
             and filed["Zinc"]["until"] == "2026-10-25"
             and filed["Vitamin C"]["status"] == "low"
             and set(filed["Vitamin D"]) == {
                 "name", "count", "form", "slot", "until", "status"},
             "meds.json filed in the fill_list schema"),
            ("### Morning: before food" in log_text
             and "- [ ] Vitamin D 1000 IU (taking)" in log_text
             and "- [ ] Zinc 15 mg (taking, short course until 2026-10-25)"
             in log_text
             and "- [ ] Vitamin C 1000 mg (low, reordered)" in log_text,
             "first log in the SKILL.md shape with dose and status words"),
            ("Elderberry, stopped 2026-10-13, bottle finished" in log_text,
             "stopped item filed"),
            (onboard.main(["--answers", os.path.join(tmp, "missing.json"),
                           "--out-dir", out_dir]) == 0,
             "bad answers file exits 0 with an honest message"),
        ]
        for ok, label in onboard_checks:
            status = "PASS" if ok else "FAIL"
            if not ok:
                failures += 1
            print("[%s] %s" % (status, label))
    print("")
    if failures:
        print("RESULT: %d failure(s)" % failures)
        return 1
    print("RESULT: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(run())
