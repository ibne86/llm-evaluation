"""Prepare or validate final inputs offline; preserve all existing selected files."""

import argparse
import json
from collections import Counter
from pathlib import Path

from llm_eval.config import ROOT
from llm_eval.evaluation_freeze import check_evaluation_freeze
from llm_eval.final_dataset import canonical_sha256, load_final_dataset, make_final_manifest, prepare_final_dataset, read_json


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Select 50 cases from the pinned cached publisher snapshot.")
    prepare.add_argument("--source", default="data/raw/dev-v2.0.json")
    prepare.add_argument("--output-dir", default="data", help="New final.json and final-manifest.json; existing files are never overwritten.")
    validate = commands.add_parser("validate", help="Check published inputs and their manifest, without raw download or inference.")
    validate.add_argument("--dataset", default="data/final.json")
    validate.add_argument("--manifest", default="data/final-manifest.json")
    validate.add_argument("--source", help="Also reproduce selection from this pinned source JSON, if available.")
    args = parser.parse_args(argv)
    root = Path(root)
    try:
        freeze = check_evaluation_freeze(root)
        freeze_hash = freeze["freeze_sha256"]
        pilot = read_json(root / "data/pilot.json")
        custom = read_json(root / "data/final-custom-cases.json")
        if args.command == "prepare":
            folder = root / args.output_dir
            paths = (folder / "final.json", folder / "final-manifest.json")
            if any(path.exists() for path in paths):
                raise ValueError("Selected dataset or manifest already exists. Preserve it; choose a new output directory for reproduction.")
            dataset = prepare_final_dataset((root / args.source).read_bytes(), pilot, custom, freeze_hash)
            manifest = make_final_manifest(dataset, pilot, custom, freeze_hash)
            folder.mkdir(parents=True, exist_ok=True)
            for path, value in zip(paths, (dataset, manifest)):
                with path.open("x", encoding="utf-8", newline="\n") as output:
                    output.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
            print(f"Prepared final inputs: {paths[0]}")
        else:
            dataset = load_final_dataset(root / args.dataset, pilot, custom, freeze_hash, root / args.manifest)
            if args.source:
                reproduced = prepare_final_dataset((root / args.source).read_bytes(), pilot, custom, freeze_hash)
                if canonical_sha256(reproduced) != canonical_sha256(dataset):
                    raise ValueError("Published cases do not reproduce from the pinned source and selection recipe.")
            print(f"Validated final inputs: {args.dataset}")
        print(json.dumps({
            "case_count": len(dataset["cases"]), "categories": dict(Counter(case["category"] for case in dataset["cases"])),
            "distinct_contexts": len({case["context"] for case in dataset["cases"]}),
            "squad_articles": dataset["metadata"]["selection"]["selected_squad_articles"],
            "dataset_sha256": canonical_sha256(dataset), "evaluation_freeze_sha256": freeze_hash,
            "source_reproduction_checked": args.command == "prepare" or bool(args.source), "model_inference_performed": False,
        }, indent=2))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"Final dataset error: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
