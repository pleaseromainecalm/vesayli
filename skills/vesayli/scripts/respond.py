#!/usr/bin/env python3
"""VeSayLi companion response rules (reference implementation).

This script is the response engine behind the VeSayLi health tracking
companion. It decides what the companion answers and what it refuses.

The engine mirrors the safety design from the VeSayLi medical-logic
review: the non-diagnostic line is enforced twice. First in the prompt,
which carries the exact non-diagnostic language. Then in a deterministic
post-processor with topic gates (kill invented sleep, energy, mood,
mobility) and never-invent guards (a med the user never mentioned is kept
but marked unverified, never silently dropped, per finding R4). See
references/guardrails.md and references/medical-logic.md.

Three layers, in order:
  1. Scripted matcher (deterministic core). Handles logging confirmations,
     capability questions, and refusals for anything diagnostic. This layer
     answers first whenever it matches.
  2. Model adapter (optional, default OFF). Targets an Ollama-compatible
     endpoint with the strict non-diagnostic system prompt. Enable with
     VESAYLI_LLM=1 and VESAYLI_LLM_MODEL set. In the companion itself the
     agent is the model, so this adapter is only for builders who want a
     local-model path.
  3. Deterministic post-processor. Runs on every model or mock reply:
     topic gates, then the diagnosis/treatment filter, then the med guard.

The engine is importable and testable without a live model. The mock path
is the default when the adapter is disabled.

Usage:
  respond.py "user text"              print JSON {input, output, refused, engine}
  respond.py --mock "user text"       force the mock model path (no network)
  respond.py --db vesayli.db "text"   also log the exchange to responses_log
  echo "text" | respond.py --stdin

Exit 0 always. No network calls unless VESAYLI_LLM=1 and VESAYLI_LLM_MODEL
are both set. There are no other network paths in this file.
"""
import json
import os
import re
import sqlite3
import sys
import urllib.request

# ---------------------------------------------------------------------------
# Canonical safe refusal. Used by the scripted layer and the post-processor.
# ---------------------------------------------------------------------------
SAFE_REFUSAL = (
    "I can't help with that one. VeSayLi tracks and organizes your health "
    "notes. It does not diagnose, interpret symptoms, or advise on treatment. "
    "Please bring this to your doctor. I can log what you're feeling so it "
    "is ready for the visit."
)

# The exact non-diagnostic language from the VeSayLi journal service.
SYSTEM_PROMPT = (
    "You are NOT a doctor. NEVER diagnose. "
    "NEVER recommend or change a medication, dose, diet, or treatment. "
    "You are the response layer of VeSayLi, a personal health tracking "
    "companion. "
    "You help the user log and organize health notes: symptoms with a "
    "severity from 0 to 10, medications taken, and free-text notes. "
    "Structure what the user said and reflect it back plainly. "
    "Never name a condition the user might have. "
    "Never interpret what symptoms mean. "
    "If the user asks for any of these, refuse in one short paragraph and "
    "tell them to talk to their doctor. Keep every reply short and plain."
)

# ---------------------------------------------------------------------------
# Layer 1: scripted matcher. Refusal triggers are checked first, always.
# Each entry: (compiled pattern, handler) where handler(match, text) returns
# (output, refused).
# ---------------------------------------------------------------------------

def _refuse(_m, _t):
    return SAFE_REFUSAL, True


def _log_symptom(m, _t):
    symptom = m.group("symptom").strip().lower()
    severity = int(m.group("sev"))
    if not 0 <= severity <= 10:
        return ("Severity needs to be between 0 and 10. Try again, for "
                "example: log headache 6/10."), False
    if not symptom:
        symptom = "symptom"
    return ("Logged. %s, %d out of 10." % (symptom, severity)), False


def _log_med(_m, _t):
    return "Logged your dose.", False


def _capabilities(_m, _t):
    return ("I log symptoms with a severity from 0 to 10, log doses you "
            "take, and keep notes. Ask me for your doctor one-pager before "
            "a visit. I don't diagnose or advise on treatment."), False


def _greet(_m, _t):
    return "Hello. What would you like to log today?", False


def _fallback(_m, _t):
    return ("I didn't catch that. I can log a symptom with a severity from "
            "0 to 10, log a dose you took, or get your doctor one-pager "
            "ready."), False


SCRIPTED = [
    # Refusal triggers first. Diagnostic questions.
    (re.compile(r"\bdo i have\b", re.I), _refuse),
    (re.compile(r"\bwhat('| i)s wrong with me\b", re.I), _refuse),
    (re.compile(r"\bwhat does (this|that|my|the)\b.*\bmean\b", re.I), _refuse),
    (re.compile(r"\bis this (serious|normal|dangerous|a sign of)\b", re.I), _refuse),
    (re.compile(r"\bcould this be\b", re.I), _refuse),
    # Treatment advice.
    (re.compile(r"\bshould i (take|stop|start|increase|decrease)\b", re.I), _refuse),
    (re.compile(r"\bwhat should i (take|do)\b", re.I), _refuse),
    (re.compile(r"\bcan i (take|stop|skip)\b", re.I), _refuse),
    (re.compile(r"\b(increase|decrease|double|halve) (my|the) dose\b", re.I), _refuse),
    (re.compile(r"\bwill .* (help|cure|fix) (my|this)\b", re.I), _refuse),
    # Safe intents.
    (re.compile(r"^(hi|hey|hello|good morning|good evening)\b", re.I), _greet),
    (re.compile(r"\b(help|what can you do|how does this work)\b", re.I), _capabilities),
    (re.compile(
        r"\b(log|record|add)\b\s+(?P<symptom>[a-z ]*?)\s*(?P<sev>\d{1,2})\s*(?:/|out of)\s*10\b",
        re.I), _log_symptom),
    (re.compile(r"\b(took|taken|just took)\b", re.I), _log_med),
]


def scripted_respond(text):
    """Return (output, refused) or None when nothing matched."""
    for pattern, handler in SCRIPTED:
        m = pattern.search(text)
        if m:
            return handler(m, text)
    return _fallback(None, text)


# ---------------------------------------------------------------------------
# Layer 3: deterministic post-processor.
# Step 1: topic gates. Kill invented sleep/energy/mood/mobility content.
# A gated topic in the reply is only allowed when the user raised it.
# Step 2: diagnosis/treatment language filter.
# Step 3: never-invent med guard with brand/generic synonym awareness.
# ---------------------------------------------------------------------------
TOPIC_GATES = {
    "sleep": ["sleep", "insomnia", "asleep", "restless"],
    "energy": ["energy", "fatigue", "exhausted", "exhaustion"],
    "mood": ["mood", "anxiety", "anxious", "depression", "depressed"],
    "mobility": ["mobility", "walking", "balance", "stairs"],
}

VIOLATIONS = [
    (re.compile(r"\byou (have|likely have|probably have|might have|seem to have|appear to have)\b", re.I),
     "diagnosis"),
    (re.compile(r"\b(this|that|it) sounds like\b", re.I),
     "diagnosis"),
    (re.compile(r"\byou should (take|stop|start|increase|decrease|try|avoid)\b", re.I),
     "treatment advice"),
    (re.compile(r"\btake \d+\s*(mg|milligrams|ml|tablets?|pills?|capsules?)\b", re.I),
     "dose instruction"),
    (re.compile(r"\b(increase|decrease|double|halve|stop) (your|the) dose\b", re.I),
     "dose change"),
]

# Brand/generic synonym map. The never-invent guard (per finding R4) keeps a
# med the patient actually mentioned instead of dropping it on a brand to
# generic mismatch. A med with no basis in the input is kept but marked
# unverified, never silently dropped.
MED_SYNONYMS = {
    "acetaminophen": ["tylenol", "paracetamol"],
    "ibuprofen": ["advil", "motrin"],
    "diphenhydramine": ["benadryl"],
    "loratadine": ["claritin"],
    "cetirizine": ["zyrtec"],
    "omeprazole": ["prilosec"],
    "propranolol": ["inderal"],
}


def topic_gate_violation(output, user_text):
    """Return the invented topic name, or None when the reply is clean."""
    low_out = output.lower()
    low_in = user_text.lower()
    for topic, keywords in TOPIC_GATES.items():
        out_hit = any(k in low_out for k in keywords)
        in_hit = any(k in low_in for k in keywords)
        if out_hit and not in_hit:
            return topic
    return None


def safety_filter(text):
    """Return (output, refused, reason or None)."""
    for pattern, reason in VIOLATIONS:
        if pattern.search(text):
            return SAFE_REFUSAL, True, reason
    return text, False, None


def _word_re(name):
    return re.compile(r"\b" + re.escape(name) + r"\b", re.I)


def mark_unverified_meds(output, user_text):
    """Keep every med the reply mentions. Tag the unverified ones.

    A med counts as verified when it or any of its brand/generic synonyms
    appears in the user's own text. Otherwise the med stays in the reply
    with an [unverified] tag. Nothing is silently dropped.
    """
    result = output
    for canonical, synonyms in MED_SYNONYMS.items():
        names = [canonical] + synonyms
        for name in names:
            if _word_re(name).search(result):
                verified = any(_word_re(n).search(user_text) for n in names)
                if not verified:
                    result = _word_re(name).sub(
                        lambda m: m.group(0) + " [unverified]", result, count=1)
                break
    return result


def post_process(output, user_text):
    """Deterministic post-processor. Returns (output, refused, reason)."""
    topic = topic_gate_violation(output, user_text)
    if topic:
        return SAFE_REFUSAL, True, "invented topic: " + topic
    filtered, refused, reason = safety_filter(output)
    if refused:
        return filtered, True, reason
    guarded = mark_unverified_meds(output, user_text)
    return guarded, False, None


# ---------------------------------------------------------------------------
# Layer 2: model adapter. Ollama-compatible. Default OFF. Only for builders
# who want a local-model path. The companion itself runs on the agent.
# ---------------------------------------------------------------------------
def llm_enabled():
    return os.environ.get("VESAYLI_LLM") == "1" and bool(os.environ.get("VESAYLI_LLM_MODEL"))


def llm_respond(text):
    """Return reply string, or None when the model is unreachable."""
    url = os.environ.get("VESAYLI_LLM_URL", "http://localhost:11434/api/generate")
    payload = json.dumps({
        "model": os.environ["VESAYLI_LLM_MODEL"],
        "system": SYSTEM_PROMPT,
        "prompt": text,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "").strip()
    except Exception:
        return None


def mock_respond(_text):
    return ("Mock model reply: I can log that for you. Tell me the symptom "
            "and a severity from 0 to 10.")


# ---------------------------------------------------------------------------
# Engine entry point.
# ---------------------------------------------------------------------------
def respond(text, use_mock=False, db_path=None):
    """Full pipeline. Returns dict with input, output, refused, engine."""
    # Layer 1: scripted core answers first.
    output, refused = scripted_respond(text)
    engine = "scripted"
    # The fallback is not a real answer, so let the LLM or mock try.
    is_fallback = output.startswith("I didn't catch that.")
    if is_fallback:
        if llm_enabled() and not use_mock:
            llm_text = llm_respond(text)
            if llm_text is None:
                output = ("The local model isn't reachable right now. I can "
                          "still log symptoms and notes for you.")
                refused = False
                engine = "scripted"
            else:
                output, refused, _reason = post_process(llm_text, text)
                engine = "llm"
        else:
            output, refused, _reason = post_process(mock_respond(text), text)
            engine = "mock"
    result = {"input": text, "output": output, "refused": refused,
              "engine": engine}
    if db_path:
        _log_exchange(db_path, result)
    return result


def _log_exchange(db_path, result):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS responses_log ("
            "id INTEGER PRIMARY KEY, input_text TEXT NOT NULL, "
            "output_text TEXT NOT NULL, refused INTEGER NOT NULL DEFAULT 0, "
            "engine TEXT NOT NULL DEFAULT 'scripted')")
        conn.execute(
            "INSERT INTO responses_log (input_text, output_text, refused, engine)"
            " VALUES (?, ?, ?, ?)",
            (result["input"], result["output"],
             1 if result["refused"] else 0, result["engine"]))
        conn.commit()
    finally:
        conn.close()


def main(argv):
    use_mock = "--mock" in argv
    argv = [a for a in argv if a != "--mock"]
    db_path = None
    if "--db" in argv:
        i = argv.index("--db")
        db_path = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if "--stdin" in argv:
        text = sys.stdin.read().strip()
    elif argv:
        text = argv[0]
    else:
        print("usage: respond.py [--mock] [--db PATH] \"text\"",
              file=sys.stderr)
        sys.exit(2)
    print(json.dumps(respond(text, use_mock=use_mock, db_path=db_path),
                     indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
