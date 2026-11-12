"""Prepare unlabelled human reviews or compare completed reviews with a saved run."""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote

from llm_eval.human_review import compare_review, comparison_markdown, create_review


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _new_file(path, content):
    """Never replace saved results or a person's existing review."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Create a review without judge scores or reasons.")
    prepare.add_argument("--results", required=True, help="Saved results.json file.")
    prepare.add_argument("--output", required=True, help="New review JSON file.")
    prepare.add_argument("--reason-policy", choices=("required", "optional"), default="required",
                         help="Use optional when written explanations will not be collected.")
    compare = commands.add_parser("compare", help="Compare human labels; no model inference.")
    compare.add_argument("--results", required=True, help="The same saved results.json file.")
    compare.add_argument("--review", required=True, help="Human-completed review JSON.")
    compare.add_argument("--output-dir", required=True, help="Folder for new comparison.json and comparison.md.")
    args = parser.parse_args(argv)
    try:
        state = _read_json(args.results)
        if args.command == "prepare":
            packet = create_review(state, reason_policy=args.reason_policy)
            _new_file(args.output, json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
            print(f"Prepared {len(packet['reviews'])} cases with no human labels: {args.output}")
        else:
            report = compare_review(state, _read_json(args.review))
            folder = Path(args.output_dir)
            paths = (folder / "comparison.json", folder / "comparison.md")
            if any(path.exists() for path in paths):
                raise ValueError("Comparison already exists. Choose a new output directory to keep previous evidence.")
            evidence = {"source_results": args.results, "human_review": args.review}
            report["evidence_files"] = {}
            for key, path in evidence.items():
                target = Path(path).resolve()
                try:
                    relative = Path(os.path.relpath(target, folder.resolve())).as_posix()
                    report["evidence_files"][key] = quote(relative, safe="/:._-~")
                except ValueError:
                    report["evidence_files"][key] = target.as_uri()
            _new_file(paths[0], json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            _new_file(paths[1], comparison_markdown(report))
            print(f"Review {report['status']}: {report['paired_decisions']}/{report['possible_pairs']} "
                  f"paired metric decisions. Reports: {folder}")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"Review error: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
