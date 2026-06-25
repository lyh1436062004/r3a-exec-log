# r3a-exec-log Sync Policy

This repository is an append-only execution log.

## Source of Truth

- `runs/round_XXXX/` is the durable source of truth.
- `analysis/round_XXXX_analysis.*` is durable per-round analysis.
- `analysis/latest_*` is only a convenience pointer and must not be written by more than one automation path.

## GitHub Actions Rule

GitHub Actions may run `tools/analyze_round.py` for validation and artifacts, but it must not commit generated `analysis/latest_*` files back to `main`.

This avoids the recurring conflict pattern:

1. Local agent commits a new round and updates `analysis/latest_*`.
2. GitHub Actions also commits `analysis/latest_*`.
3. The next local push becomes non-fast-forward and rebase conflicts on the same files.

## Local Push Rule

Before pushing:

1. `git fetch origin main`
2. `git rebase origin/main`
3. `git push origin main`
4. Verify remote head with `git ls-remote origin refs/heads/main`

Never force-push. Never overwrite an existing `runs/round_XXXX/` directory.
