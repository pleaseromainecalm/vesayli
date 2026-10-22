# VeSayLi

VeSayLi by Please Romaine Calm. Pronounced Veh-SAY-lee, after Vesalius, the anatomist.

## The story

VeSayLi started as David Romaine's personal health tracking project. A place to dump appointment transcriptions, prescriptions, and meds, and get a daily med and supplement tracker he could just talk to. No forms, no signup, no setup.

It went through an offline app phase: a finished SwiftUI app, 41 of 41 tests green, retired in August 2026 before it ever shipped. That phase is parked, not dead. See `references/PARKED.md`.

Now it is a skill. It teaches any Muse to be a personal health tracking companion from Day 1. The user talks, the companion organizes: meds, symptoms, notes, and a weekly summary for the doctor. The product battle is trust, not tools.

## The trust contract in one paragraph

The companion is honest about data: on a standard VM, conversations are not end to end encrypted, may be logged and reviewed by Meta, and contribute to AI development unless the user opts out. It asks before remembering anything health related, shows what it stores, and deletes on request. The daily log is a readable file the user owns. It tracks and organizes. It never diagnoses, prescribes, or changes doses. The more the user trusts it, the more airtight that line stays.

## What is in this skill

- `SKILL.md`: the method. Day-1 start, the daily log, the trust contract, the daily practice, the guardrail pattern, memory hygiene.
- `skill.yaml`: skill metadata.
- `references/guardrails.md`: the medical advice line spec the response engine enforces.
- `references/medical-logic.md`: the double enforced safety design and the correctness checklist, ported from the June 2026 medical logic review.
- `references/privacy-model.md`: the verified privacy claims and hardening checklist from the June 2026 audit, written for the app phase.
- `references/PARKED.md`: the retired offline app phase. Parked 2026-10-19, not dead.
- `scripts/respond.py`: the companion's response rules. Refusal triggers, scripted answers, the non diagnostic post processor.
- `scripts/one_pager.py`: the flagship output. Renders a doctor one pager from a folder of daily logs.
- `scripts/one_pager_html.py`: the same one pager as a styled, printable HTML file.
- `scripts/onboard.py`: files the Day-1 interview into a meds file and a first daily log.
- `scripts/fill_list.py`: the weekly fill list for the fill-and-check ritual.
- `scripts/visit_prep.py`: questions for the doctor, built from the user's own logged words.
- `scripts/refill_watch.py`: flags meds and supplements running low.
- `scripts/pack_list.py`: a travel pack list from the meds file.
- `scripts/test_harness.py`: exercises the engine and the one pager.
- `assets/`: the locked logo (a voice waveform running into a heartbeat on deep purple), the icon, and the wordmark.
- `LICENSE`: Apache-2.0.

## Quickstart

Talk to the engine:

```
python3 scripts/respond.py "log headache 6/10"
python3 scripts/respond.py "should I take ibuprofen?"
```

Make a daily log and render the weekly one-pager:

```
mkdir -p logs
cat > logs/log-2026-10-19.md << 'EOF'
# 2026-10-19

## Meds and supplements
- [x] Vitamin D 1000 IU, morning
- [ ] Magnesium 200 mg, evening

## How today feels
- Tired but okay. Headache around noon, 4 out of 10.

## Notes
- Cardio appointment booked for Thursday.
EOF
python3 scripts/one_pager.py logs/ --days 7
```

Run the test harness:

```
python3 scripts/test_harness.py
```

## Name and logo status

Name locked 2026-10-19: VeSAYLi, used the same way everywhere. Logo locked 2026-10-22: a voice waveform running into a heartbeat on deep purple, over the VESAYLI wordmark with SAY in cyan. See `assets/logo.png`.

## Network use

All scripts run locally and read or write only the files you point them at. The one exception is `scripts/respond.py`, which is off by default. If you set `VESAYLI_LLM=1` and `VESAYLI_LLM_MODEL`, it sends the user's text to `VESAYLI_LLM_URL` (default `http://localhost:11434`, a local Ollama). If you point that URL at a remote server, health text leaves the device. Keep it local.

## License

Apache-2.0. See LICENSE. The license covers the code and docs in this module. It does not grant any trademark. No Meta endorsement is implied.
