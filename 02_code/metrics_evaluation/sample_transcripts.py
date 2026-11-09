#!/usr/bin/env python3
"""Draw a reproducible sample of two transcripts from each condition cell."""

import argparse
import csv
import random
import subprocess
import tempfile
import textwrap
from collections import defaultdict
from pathlib import Path


CELLS = {
    (condition, mode)
    for condition in ("low", "moderate", "high")
    for mode in ("treatment", "baseline")
}
REPO_ROOT = Path(__file__).resolve().parents[2]


def markdown_to_pdf(source: Path, target: Path, header: str) -> None:
    lines = [header, ""]
    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        wrapped = textwrap.wrap(
            line.expandtabs(4),
            width=45,
            break_long_words=False,
            break_on_hyphens=False,
        )
        lines.extend(wrapped or [""])

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", encoding="utf-8", delete=False
    ) as temporary:
        temporary.write("\n".join(lines) + "\n")
        temporary_path = Path(temporary.name)

    try:
        with target.open("wb") as output:
            subprocess.run(
                [
                    "cupsfilter",
                    "-m",
                    "application/pdf",
                    "-o",
                    "media=A4",
                    "-o",
                    "page-left=72",
                    "-o",
                    "page-right=72",
                    "-o",
                    "page-top=72",
                    "-o",
                    "page-bottom=72",
                    str(temporary_path),
                ],
                check=True,
                stdout=output,
                stderr=subprocess.DEVNULL,
            )
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--metrics-csv",
        type=Path,
        default=REPO_ROOT
        / "01_data/processed/simulation_metrics_final_200_plus_low_high_baseline.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "01_data/processed/transcript_sample_12",
    )
    parser.add_argument("--seed", type=int, default=20261021)
    args = parser.parse_args()

    runs = defaultdict(list)
    with args.metrics_csv.open(encoding="utf-8", newline="") as file:
        metric_rows = csv.DictReader(file)
        for row in metric_rows:
            if row.get("status") != "completed":
                continue

            metadata_path = REPO_ROOT / row["metadata_file"]
            run_dir = metadata_path.parent
            chat_path = run_dir / "chat.md"

            if not chat_path.exists():
                continue

            cell = (
                row["context_transparency_condition"],
                row["smm_mode"],
            )
            if cell in CELLS:
                runs[cell].append((row, chat_path))

    rng = random.Random(args.seed)
    args.output.mkdir(parents=True, exist_ok=True)
    selected = []

    for cell in sorted(CELLS):
        candidates = sorted(runs[cell], key=lambda item: item[0]["run_id"])
        if len(candidates) < 2:
            raise RuntimeError(f"Weniger als zwei Runs in {cell}")
        selected.extend((cell, item) for item in rng.sample(candidates, 2))

    rows = []
    for number, ((condition, mode), (source_row, source)) in enumerate(selected, 1):
        run_id = source_row["run_id"]
        target = args.output / f"sample_{number:02d}.pdf"
        markdown_to_pdf(source, target, f"Sample {number}")
        rows.append(
            {
                "sample_id": f"sample_{number:02d}",
                "run_id": run_id,
                "condition": condition,
                "smm_mode": mode,
                "communication_score": source_row["team_process_communication"],
                "cooperation_score": source_row["team_process_cooperation"],
                "transcript": str(target),
            }
        )

    for old_markdown in args.output.glob("sample_*.md"):
        old_markdown.unlink()

    with (args.output / "sample_manifest.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(selected)} Transkripte geschrieben nach {args.output}")


if __name__ == "__main__":
    main()
