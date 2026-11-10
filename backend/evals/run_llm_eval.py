"""Real local-model eval (Ollama). Synthetic contracts written for testing; not real clients."""
import json, sys, time
from datetime import date
sys.path.insert(0, ".")
from app.extraction import ollama_extract, validate_plan

CONTRACTS = {
 "clean_3_milestones": """Agreement between Nordwind GmbH (accounts@nordwind.example) and the contractor for a React dashboard.
The total fee is USD 2,400.
Phase 1 - Wireframes: USD 600, due by 2026-11-25.
Phase 2 - Frontend build: USD 1,200, due by 2026-12-10.
Phase 3 - QA and deployment: USD 600, due by 2026-12-22.""",
 "prose_with_ambiguity": """Hi! As discussed, BrightLoop Inc (finance@brightloop.example) will pay you USD 900 in total for the landing page.
We'll pay USD 300 upfront when you start on 2026-11-15, and the remaining USD 600 once the site goes live, targeted for 2026-12-01.
Hosting costs may be reimbursed later if approved by our manager.""",
 "sum_mismatch_trap": """Contract with Sato Design LLC (pay@sato.example). Project budget: USD 1,000.
Milestone A: logo concepts, USD 450, due 2026-11-30.
Milestone B: brand guide, USD 450, due 2026-12-15.
A final bonus of USD 100 may be paid at the client's discretion.""",
}
if __name__ == "__main__":
    res = []
    for name, text in CONTRACTS.items():
        t = time.time()
        try:
            plan = ollama_extract(text, "http://127.0.0.1:11434", "qwen2.5:3b-instruct")
            errs = validate_plan(plan, text, date(2026, 11, 8))
            out = {"plan": plan.model_dump(), "errors": errs}
        except Exception as e:
            out = {"exception": repr(e)[:300]}
        out.update(name=name, seconds=round(time.time() - t, 1))
        res.append(out)
        print(json.dumps(out, indent=1))
    json.dump(res, open("evals/llm_eval_results.json", "w"), indent=1)
    