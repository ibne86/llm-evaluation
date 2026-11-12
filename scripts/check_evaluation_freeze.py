"""Verify the frozen protocol and installed packages; no Ollama connection or inference."""

import argparse
import json

from llm_eval.evaluation_freeze import check_evaluation_freeze


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Config path, relative to the project or absolute; only dataset may differ.")
    args = parser.parse_args(argv)
    try:
        result = check_evaluation_freeze(config_path=args.config)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"Freeze check failed: {error}")
        return 2
    print(json.dumps(result, indent=2))
    print("Protocol check passed. Live Ollama/models and the final dataset have not been checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
