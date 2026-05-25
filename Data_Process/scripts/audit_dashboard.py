"""
Step 8b — Human audit dashboard (CLI).

Walks the 'partial' bucket, shows each entry's score breakdown and reasoning,
lets you mark each as ACCEPT / REJECT / EDIT. Persists decisions to:
  08_output/audit_decisions.jsonl
"""
import json, importlib.util, sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("config", Path(__file__).parent / "00_config.py")
config = importlib.util.module_from_spec(spec); spec.loader.exec_module(config)

PARTIAL = config.OUTPUT / "partial.jsonl"
DECISIONS = config.OUTPUT / "audit_decisions.jsonl"

if not PARTIAL.exists():
    print("No partial.jsonl found. Run the pipeline first.")
    sys.exit(1)

records = [json.loads(l) for l in open(PARTIAL)]
already_decided = set()
if DECISIONS.exists():
    for l in open(DECISIONS):
        already_decided.add(json.loads(l)["id"])
    print(f"Resuming — {len(already_decided)} already decided")

todo = [r for r in records if r["id"] not in already_decided]
print(f"{len(todo)} entries remaining to audit")

with open(DECISIONS, "a") as out:
    for i, r in enumerate(todo):
        print("\n" + "="*70)
        print(f"[{i+1}/{len(todo)}]  id={r['id']}  score={r['score']}  category={r['category']}")
        print(f"  source={r['source']}")
        if r.get("freq_hz"):
            print(f"  freq={r['freq_hz']/1e6:.3f} MHz  country={r.get('country')}")
        if r.get("question"):
            print(f"  Q: {r['question'][:200]}")
        if r.get("answer"):
            print(f"  A: {r['answer'][:300]}")
        print(f"  llm_verdict={r.get('llm_verdict')}  fact_check={r.get('fact_check')}")
        print(f"  score_breakdown={r['score_breakdown']}")

        while True:
            choice = input("\n[a]ccept / [r]eject / [e]dit / [s]kip / [q]uit > ").strip().lower()
            if choice in ("a","r","e","s","q"): break
        if choice == "q":
            print("Bye.")
            sys.exit(0)
        if choice == "s":
            continue
        decision = {"id": r["id"], "decision": {"a":"accept","r":"reject","e":"edit"}[choice]}
        if choice == "e":
            note = input("Edit note: ").strip()
            decision["edit_note"] = note
        out.write(json.dumps(decision) + "\n")
        out.flush()
        print(f"  → recorded: {decision['decision']}")

print("\nDone.")
