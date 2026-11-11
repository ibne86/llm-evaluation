"""Preview or execute a bounded repeatability check on existing pilot cases."""

import argparse
import json

from llm_eval.config import ROOT, load_config
from llm_eval.consistency import make_plan, summarize_consistency
from llm_eval.dataset import load_dataset


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Optional baseline configuration TOML path.")
    parser.add_argument("--repeats", type=int, choices=range(2, 6), help="Repeats per case; default 3 for a new run.")
    parser.add_argument("--case-id", action="append", help="Repeat to select explicit pilot IDs in the given order.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="Preview the plan without contacting Ollama.")
    mode.add_argument("--resume", help="Continue a saved consistency run with unchanged inputs and settings.")
    mode.add_argument("--summary", help="Read a consistency run without model inference.")
    args = parser.parse_args(argv)
    try:
        if args.plan:
            config = load_config(args.config)
            plan, cases = make_plan(load_dataset(ROOT / config["dataset"]), args.repeats or 3, args.case_id)
            print(json.dumps({**plan, "questions": [{"case_id": case["case_id"], "category": case["category"], "question": case["question"]} for case in cases],
                              "answer": config["answer"], "judge": config["judge"], "thresholds": config["thresholds"]}, indent=2))
            return 0
        from llm_eval.consistency_runner import read_consistency_run, run_consistency
        if args.summary:
            if args.repeats is not None or args.case_id is not None or args.config:
                raise ValueError("--summary reads saved settings; omit configuration/selection overrides.")
            print(json.dumps(summarize_consistency(read_consistency_run(args.summary)[1]), indent=2))
            return 0
        return run_consistency(args.config, args.repeats, args.case_id, args.resume)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"Consistency input error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
