# Context Broker

Deterministic context waterfall. Order matters — do not jump to full files first.

```
0. AUTHORITY            CONSTITUTION.md → spec → ADR → ROADMAP/STATE
1. EXACT LEXICAL        rg / rg --json
2. STRUCTURAL           ast-grep (sg)
3. SYMBOLS/REFERENCES   only if a future code-intelligence owner is enabled
4. GRAPH/IMPACT         only if enabled AND needed (not installed in v1)
5. EXACT SOURCE RANGES  the specific lines/symbols that matter
6. FULL FILE            only when justified
```

## Commands

```bash
# exact lexical search (machine-readable)
rg --json -n '<pattern>' <path>

# structural search (Python)
ast-grep -p '<pattern>' -l python <path>

# structural rewrite (dry-run: no --rewrite)
ast-grep -p '<pattern>' --rewrite '<replacement>' -l python <path>
```

## Rules

- Prefer `rg --json`, `git --porcelain`, bounded pytest output, `jq` before summarizing.
- No silent truncation: if output is cut, mark `truncated=true` and keep a path to raw evidence.
- Record provenance for important context items (source, path, lines, authority level, reason).
- Re-reads are allowed but telemetry marks `reread`; a high reread rate signals poor retrieval.

Soft dynamic-context target: ~5–20K useful tokens (a diagnostic signal, not a hard limit).
