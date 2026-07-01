#!/usr/bin/env bash
# Deterministic PRTOE config banner for local CodeRabbit CLI runs.
# The `cr` CLI does not print high_level_summary or path_instructions to the
# terminal; this wrapper prints the banner immediately, then execs `cr`.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
yaml="${repo_root}/.coderabbit.yaml"

if [[ -f "$yaml" ]]; then
  echo "✓ PRTOE .coderabbit.yaml ACTIVE — physics-first | CONTEXT.md + PRTOE_PHYSICS_FOR_REVIEW.md | no auto-patches"
else
  echo "✗ CONFIG NOT LOADED — missing ${yaml}"
fi

exec cr "$@"