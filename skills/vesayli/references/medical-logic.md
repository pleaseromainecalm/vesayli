# VeSayLi medical logic

VeSayLi by Please Romaine Calm.

Note, October 2026: the offline dogma this review served is parked (see PARKED.md). The double enforced safety design is still the safety core. The trust contract in SKILL.md is the framing now.

Ported from `code-review-medical-logic.md`, the June 18, 2026 review of the VeSayLi journal service, chat session, and care journal code. This is a plain language port. The full review has the file and line detail.

## The double enforced safety design

The non diagnostic safety line is enforced twice.

First, in the prompt. The journal service prompt carries the exact words: "You are NOT a doctor. NEVER diagnose. NEVER recommend or change a medication, dose, diet, or treatment."

Second, in a deterministic post processor. It runs topic gates that kill invented sleep, energy, mood, and mobility content. It runs never invent guards that block invented meds, foods, and symptoms. It never infers a symptom from a med type.

Third, by construction. The daily checklist deliberately ignores the model's free form summary, so it cannot tick a symptom the patient never said.

The scripts in this skill mirror this design. `respond.py` carries the prompt language, the topic gates, and the never invent guards. `test_harness.py` exercises them.

## Correctness checklist

These findings are correctness and data integrity gaps for a medical record, ordered by patient impact. Work them before any release.

- R1. Atomic saves. The save routine deleted the old entry before writing the new one, and swallowed write errors. A failed write could erase a day's log silently. Build the new outcome first, delete the old one only after the write succeeds, and surface save failures to the patient.
- R2. Twice daily meds. Three spots assumed one dose per med per day, so a morning and an evening dose of the same med collapsed into one. Key meds by name plus time, not name alone, and iterate all daily occurrences.
- R3. Durable corrections. Removing a symptom chip corrected the analysis but the words stayed in the transcript, so the next turn re extracted the deleted symptom and the chip came back. Track removed items in a per day suppression set, or re analyze only the new turn and merge.
- R4. Brand and generic synonyms. The never invent guard dropped a med when the model normalized a brand to a generic (patient said Tylenol, model wrote acetaminophen). Allow a brand to generic synonym pass, or keep the med and mark it unverified rather than dropping it. This skill's `respond.py` implements the mark unverified path.
- R5. Rough day overwrite. Tapping "Rough day" replaced anything already logged that day. Only write the minimal entry when the day has no entry yet, or merge.
- R6. Follow up budget. The gentle follow up budget field was declared but never enforced. Implement the cap or delete the field.
- R7. Silent writes. CareKit writes swallowed errors, so a failed save looked like success. Log failures and consider a lightweight could not save signal.
- R8. Checklist matching. The checklist used substring matching, which can false match inside a larger word. Use word boundary matching.
