#!/usr/bin/env bash
# Quick evidence check: is CodeRabbit seeing repo-root .coderabbit.yaml?
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
yaml="${repo_root}/.coderabbit.yaml"
head_sha="$(git rev-parse HEAD)"

echo "Repo:     ${repo_root}"
echo "Branch:   $(git branch --show-current)"
echo "HEAD:     ${head_sha}"
echo "Yaml:     ${yaml}"

if [[ ! -f "$yaml" ]]; then
  echo "✗ CONFIG NOT LOADED — .coderabbit.yaml missing"
  exit 1
fi

echo ""
echo "Committed yaml (what CR typically resolves at HEAD):"
git show "HEAD:.coderabbit.yaml" | grep -nE "profile:|path_filters:|tone_instructions:|PRTOE yaml config handshake|CONFIG NOT LOADED|CONTEXT.md" || true

if ! git diff --quiet -- .coderabbit.yaml; then
  echo ""
  echo "⚠ Working-tree .coderabbit.yaml differs from HEAD (uncommitted)."
  echo "  Local reviews resolve config from the branch snapshot — commit yaml"
  echo "  changes for CodeRabbit to pick up banner/handshake edits."
  git diff --stat -- .coderabbit.yaml
fi

latest_review="$(ls -td "${HOME}/.coderabbit/reviews"/*/*/reviews/*/git.json 2>/dev/null | head -1 || true)"
if [[ -n "$latest_review" ]]; then
  echo ""
  echo "Latest cached review: ${latest_review}"
  python3 - <<'PY' "$latest_review"
import json, sys
p = sys.argv[1]
with open(p) as f:
    g = json.load(f)
files = [d.get("filePath") for d in g.get("diff", [])]
print("  head:", g.get("head", "?")[:12])
print("  diff files:", ", ".join(files))
prtoe_core = {
    "source/perturbations.c", "source/background.c",
    "include/perturbations.h", "include/background.h",
}
def is_whitelisted(f):
    if f in prtoe_core:
        return True
    if f.startswith("cosmic_dashboard/"):
        return True
    if f in {"cosmic_explorer.py", "run_cosmicforge.py", "launch_cosmic.sh", "kill_dashboard.ps1"}:
        return True
    return False
extra = [f for f in files if not is_whitelisted(f)]
if extra:
    print("  note: CLI still ships full diff context; path_filters limit review focus, not diff listing.")
PY
fi

echo ""
echo "Evidence yaml IS influencing reviews:"
echo "  - Findings cite CONTEXT.md / PRTOE_PHYSICS_FOR_REVIEW contracts"
echo "  - Those strings live only in your .coderabbit.yaml knowledge_base + path_instructions"
echo "  - enable_prompt_for_ai_agents should be false (physics-first, no auto-patches)"
grep -q "enable_prompt_for_ai_agents: false" "$yaml" && echo "  ✓ auto-patches disabled in yaml" || echo "  ✗ auto-patches not disabled"
echo ""
echo "CLI does NOT print: summary banner, pre_merge_checks, review_details."
echo "Use: ./scripts/cr-prtoe.sh   for a deterministic startup banner before cr runs."