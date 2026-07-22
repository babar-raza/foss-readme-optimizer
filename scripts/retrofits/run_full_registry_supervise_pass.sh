#!/usr/bin/env bash
# Wave 8e (decision #42): the full `data/products.json` live-proof pass --
# `readme-agent supervise --repo ... --durable-state` against all 25 real
# registry entries, not the 3-5-repo samples every prior wave's live proof
# used. Read-only/audit machinery (all 9 domains' classify/audit steps)
# is exercised against every entry regardless of mode (decision #24/
# PIL-011); the one real write (commit_readme_write) only ever fires for
# the 2 mode:"full" entries, per the unchanged access constraint in
# AGENTS.md -- this is not, and must never be described as, proof of 25
# real commits.
#
# Requires the OPS-009 local git-credential workaround already applied to
# this project's own repo (durable state pushes to this project's own
# remote, never a target repo) -- applied once for this whole pass,
# removed immediately after, matching the "one credential dance, not one
# per sub-wave" precedent Wave 7b-7e established.
#
# Kept after use as the executable record of this verification -- see
# plans/GOVERNANCE.md, "Repository layout", placement rule 5.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

LOG_DIR="runs/full-registry-pass-2026-07-21"
mkdir -p "$LOG_DIR"
SUMMARY="$LOG_DIR/summary.tsv"
echo -e "org_repo\tstatus\telapsed_seconds\texit_code" > "$SUMMARY"

REPOS=(
  "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
  "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
  "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
  "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript"
  "aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python"
  "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp"
  "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
  "aspose-cells-foss/Aspose.Cells-FOSS-for-.NET"
  "aspose-cells-foss/Aspose.Cells-FOSS-for-Python"
  "aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript"
  "aspose-email-foss/Aspose.Email-FOSS-for-Cpp"
  "aspose-email-foss/Aspose.Email-FOSS-for-.Net"
  "aspose-email-foss/Aspose.Email-FOSS-for-Python"
  "aspose-font-foss/Aspose.Font-FOSS-for-Python"
  "aspose-note-foss/Aspose.Note-FOSS-for-Python"
  "aspose-page-foss/Aspose.Page-FOSS-for-Python"
  "aspose-pdf-foss/aspose-pdf-foss-for-go"
  "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java"
  "aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET"
  "aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp"
  "aspose-slides-foss/Aspose.Slides-FOSS-for-Java"
  "aspose-slides-foss/Aspose.Slides-FOSS-for-.NET"
  "aspose-slides-foss/Aspose.Slides-FOSS-for-Python"
  "aspose-tex-foss/Aspose.TeX-FOSS-for-Python"
  "aspose-words-foss/Aspose.Words-FOSS-for-Python"
)

i=0
total=${#REPOS[@]}
for org_repo in "${REPOS[@]}"; do
  i=$((i + 1))
  safe_name="${org_repo//\//__}"
  out_file="$LOG_DIR/${safe_name}.log"
  echo "[$i/$total] $org_repo -- starting"
  start=$(date +%s)
  ./.venv/Scripts/python.exe -m readme_agent.cli supervise --repo "$org_repo" --durable-state \
    > "$out_file" 2>&1
  exit_code=$?
  end=$(date +%s)
  elapsed=$((end - start))
  status="unknown"
  if grep -q "CONVERGED_NO_CHANGE" "$out_file" 2>/dev/null; then
    status="CONVERGED_NO_CHANGE"
  elif grep -qi "traceback" "$out_file" 2>/dev/null; then
    status="TRACEBACK"
  fi
  echo -e "${org_repo}\t${status}\t${elapsed}\t${exit_code}" >> "$SUMMARY"
  echo "[$i/$total] $org_repo -- done in ${elapsed}s (exit ${exit_code}, status ${status})"
done

echo "All done. Summary at $SUMMARY"
