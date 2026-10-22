# VeSayLi privacy model

VeSayLi by Please Romaine Calm.

Note, October 2026: the offline dogma this audit served is parked (see PARKED.md). The verified claims and the honesty standard still stand. The trust contract in SKILL.md is the framing now.

Ported from `privacy-threat-model.md`, the June 18, 2026 audit of the VeSayLi SwiftUI codebase. This is a plain language port. For the full audit detail, read the source doc.

## The verified claims

Each claim below was verified against the shipping Swift code. That is what makes them marketing safe.

| Claim | What the code showed | Status |
|---|---|---|
| Your words never leave this device. Nothing is uploaded. | No URLSession or networking APIs anywhere in the Swift sources | Verified |
| No tracking. Data not collected. | No Firebase, Sentry, Amplitude, or analytics SDKs | Verified |
| No account. No subscription. | No auth or sign in code | Verified |
| On device AI only, locked to the on device model. | SystemLanguageModel runs Foundation Models locally. No Private Cloud Compute wired in. | Verified (today) |
| Non diagnostic. Structuring, never diagnosis. | The journal service prompt reads "You are NOT a doctor. NEVER diagnose. NEVER recommend or change a medication, dose, diet, or treatment." | Verified |
| Your private iCloud, if you choose to sync. | CloudKit not implemented yet, comment only | Forward looking |

The marketing safe statement, fully backed by the audit: "VeSayLi sends nothing to any server, runs its AI entirely on your device, has no account and no tracking, and never diagnoses."

## Why the posture holds

The attack surface is narrow. There is no backend, no CI or CD, no secrets, no webhooks. The real surface is the on disk health store, user initiated export and share, the on device AI, and future opt in sync features that are not built yet. Dependencies are first party Apple only, which keeps supply chain risk small.

## Pre launch hardening checklist

These findings are pre launch hardening and claim honesty maintenance, not breaches. Work them before any release.

- F1. Health store file protection. The CareKit store relied on iOS default protection, not complete protection. Set NSFileProtectionComplete on the store file and its sidecars so the database stays encrypted while the device is locked.
- F2. Entitlements and sandbox. No code sign entitlements were set and the macOS build was not sandboxed. Add an entitlements file with complete data protection on iOS, plus App Sandbox and Hardened Runtime on macOS. This also gates Mac App Store distribution.
- F3. Clipboard health data egress. Copying an entry used the general pasteboard, which any app can read and which syncs to other devices over Universal Clipboard. Use local only pasteboard items with an expiration date for health data, or prefer a user controlled share sheet. Update the privacy copy to say user initiated copy and share leaves the device by the user's choice.
- F4. Claims review checkpoint. "Nothing is uploaded" is fully true today. When CloudKit sync or Private Cloud Compute ship, the strongest claims and the App Store data label must be re evaluated. Wire a claims review checkpoint into those work items and gate the strongest claims behind the on device only build.
- F5. AI safety net. The non diagnostic guardrail is prompt level, which can drift. Keep the deterministic post processor and the test harness as the safety net.

## A note on the source

The source audit was an AI assisted scan, not a professional security audit. It is a first pass risk reduction between professional audits. For a health app handling personal data before launch, get a qualified security and privacy firm as a second pass.
