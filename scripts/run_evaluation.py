"""Run the development pilot, resume it, or read a saved summary."""

import argparse
import json

from llm_eval.runner import read_run, run_pilot
from llm_eval.reporting import summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Optional configuration TOML path.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--resume", help="Continue an interrupted run with unchanged settings and code.")
    mode.add_argument("--reuse-responses", help="Create a new scoring run using compatible saved responses.")
    mode.add_argument("--summary", help="Read an existing run folder without model inference.")
    args = parser.parse_args()
    if args.summary:
        _, state = read_run(args.summary)
        print(json.dumps(summarize(state), indent=2))
        return 0
    return run_pilot(args.config, args.resume, args.reuse_responses)


if __name__ == "__main__":
    raise SystemExit(main())
