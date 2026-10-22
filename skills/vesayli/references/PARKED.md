# Parked: the offline app phase

Parked 2026-10-19. Not dead.

## What it was

VeSayLi as an offline-first app. A native SwiftUI app for iOS and macOS, one project shipped together. On device transcription with SpeechAnalyzer. On device structuring with Apple Foundation Models, locked to the device, no cloud compute wired in. CareKit (OCKStore) as the single source of truth for care plan, tasks, schedules, outcomes, and contacts. Export by the user: Markdown and PDF doctor reports. No backend, no account, no server.

The privacy architecture was verified against the shipping code by a June 2026 audit: no network APIs, no tracking SDKs, no auth code, on device AI only, non diagnostic by prompt. The build was finished and tested: 41 of 41 tests green, zero warnings. It was retired in August 2026 before shipping. Never signed, no TestFlight build, no Apple Developer account.

It shipped an 8 condition template library (POTS, Long Covid and Neuro Covid, Fibromyalgia, ME/CFS, hEDS, MCAS, Migraine, Anxiety and low mood, plus Core), a chat style home screen, a medications screen with tap to mark taken, and a doctor summary export.

## What is parked with it

- The offline-only dogma: health data must never touch the cloud or the chat.
- The SwiftUI plus CareKit target shape.
- The app store path: Apple Developer membership, TestFlight, App Store review.
- Trademark and domain planning: the trademark was never filed, domains and handles were never secured, the support email never moved off a personal Gmail, the icon was never picked.
- The redirect rule that refused health data in chat by design.

## Why it is parked

The fortress framing lost the plot. The point was always a simple tool people can use from Day 1 with a companion they trust. Worrying about keeping everything perfectly offline was losing the convenience and appeal of what the thing is for: helping the people who need it most.

## What survives

- The guardrail design (`medical-logic.md`, `guardrails.md`): the double enforced non diagnostic line. Still the safety core.
- The privacy audit's honesty standard: state data reality plainly, never oversell a claim.
- The caregiver access principle: carried forward into SKILL.md.
- The 8 condition templates and the daily log shape: reusable whenever a build needs them.

## To unpark

David's call. The SwiftUI codebase lives with him. The checklists are in `references/`.
