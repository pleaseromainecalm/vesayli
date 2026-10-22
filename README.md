# VeSayLi

*Just say it. I'll keep track.*

VeSayLi by Please Romaine Calm.

A skill that teaches any AI agent to be a personal health-tracking companion from Day 1. No setup, no signup, no forms. The user talks, the companion organizes. The product battle is trust, not tools.

## Install

```bash
npx skills add pleaseromainecalm/vesayli --skill vesayli
```

The CLI finds `skills/vesayli/SKILL.md` and installs it into your agent. Works with any agent that reads the open SKILL.md standard (Claude Code, Cursor, and the rest). Or copy the `skills/vesayli/` folder into your agent's skills directory by hand.

## What it does

- **Day-1 interview.** The first conversation is the setup: meds, timing, today's log. No intake form.
- **Daily log.** Time-slotted med tracking with plain status words (taken, low, out), plus a stopped-meds history that never gets deleted.
- **Weekly fill-and-check ritual.** A guided two-pass practice: fill the box, then check it, read back like a pilot.
- **Doctor one-pager.** Renders a readable summary from the logs in markdown and printable HTML.
- **Visit prep, refill watch, travel pack.** Small practices built on the same log.
- **Trust contract.** Ask before keeping anything. Show everything kept. Delete fully on request. Practice turns are test-only unless the user says keep.
- **Non-diagnostic, twice enforced.** The prompt words plus a deterministic post-processor. It organizes and reminds. It never diagnoses, prescribes, or changes a dose.

## Layout

```
skills/vesayli/
  SKILL.md            the method (with open-standard frontmatter)
  skill.yaml          Muse metadata
  references/         guardrails, medical logic, privacy model, parked ideas
  scripts/            the guardrail engine, one-pager renderers, fill/pack/refill tools, tests
  assets/             icon, wordmark and logo
```

## License

Apache 2.0. See LICENSE. Opening the code does not give away the name: trademark rights are excluded under Section 6.
