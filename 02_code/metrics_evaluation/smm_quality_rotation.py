#!/usr/bin/env python3
"""Calculate SMM quality metrics for the A/C label-rotated task."""

from __future__ import annotations

import sys

import smm_quality as base


base.SMM_QUALITY_METHOD = "rotated_ac_decisive_evidence_coverage_x_memory_similarity"
base.C_DECISIVE_EVIDENCE_PATTERNS = [
    r"100\s*%\s*reliable|100 percent reliable|100.*reliable",
    r"positive atmosphere|crew atmosphere|positive.*crew",
    (
        r"calm in a crisis|stays calm|keeps calm|calm under pressure|"
        r"calmness under pressure"
    ),
    r"understands complicated technology|complicated technology",
    r"concern for others|others above everything|puts concern",
    r"excellent attention|attention skills|attention",
]


def main() -> int:
    """Run the base SMM quality calculator with rotated-task metadata labels."""
    return base.main()


if __name__ == "__main__":
    sys.exit(main())
