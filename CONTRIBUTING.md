# Contributing

1. Run `uv sync --all-packages`, then `uv run pytest`.
2. Reuse first. Before adding a feature, check Mem0, Graphiti and existing packages. If you write original code
   that overlaps upstream functionality, add a "why not reuse" line to `docs/provenance.md`.
3. Keep upstream versions pinned. Bumping one requires the test suite to pass and an update to
   `docs/upstream-feature-matrix.md`.
4. Never copy AGPL code (e.g. Honcho) into this repository.
5. Claims in the docs must match tested behavior. Update `docs/status.md` with every feature change.
6. Keep commits small and descriptive, one logical change each.
