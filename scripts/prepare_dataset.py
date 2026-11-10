"""Prepare only the 10-case pilot from the publisher's SQuAD dev JSON."""

import argparse
import json
from pathlib import Path
from urllib.request import urlopen

from llm_eval.dataset import SOURCE_URL, prepare_pilot

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Fetch the publisher's dev JSON if absent.")
    args = parser.parse_args()
    raw_path = ROOT / "data" / "raw" / "dev-v2.0.json"
    output = ROOT / "data" / "pilot.json"
    if output.exists():
        raise SystemExit("pilot.json already exists. Preserve it; do not silently replace a selected dataset.")
    if not raw_path.exists():
        if not args.download:
            raise SystemExit("The source is absent. Run with --download once.")
        with urlopen(SOURCE_URL, timeout=60) as response:
            raw = response.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise SystemExit("The source exceeded the expected download size.")
        dataset = prepare_pilot(raw)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(raw)
    else:
        dataset = prepare_pilot(raw_path.read_bytes())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(dataset['cases'])} development cases: {output}")
    print(f"Source SHA-256: {dataset['metadata']['source_sha256']}")
    for case in dataset["cases"]:
        print(f"{case['category']}: {case['case_id']} | {case['source'].get('article_title', 'custom')}")
    print("No final 50-case evaluation dataset was prepared.")


if __name__ == "__main__":
    main()
