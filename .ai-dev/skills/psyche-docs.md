# psyche-docs  (conditional)

WHEN TO USE: a task requires creating/updating durable project documentation.

INPUTS: the change, canonical doc conventions (docs/).

STEPS:
1. Check authority for where the doc belongs (docs/development, docs/implementation, ...).
2. Update only the affected doc; keep verbatim/normalized/derived separation.
3. Validate YAML/links/terminology and absence of secrets/personal data (AGENTS.md).

OUTPUT: updated doc(s) consistent with project conventions.

STOP CONDITIONS: do not edit READ-ONLY canonical inputs
(`docs/AI_DEV_OS_V1.md`, `docs/AI_DEV_OS_RESEARCH_CATALOG_V1.docx`).

ALLOWED TOOLS: Read, Write, Edit, rg.

FORBIDDEN SIDE EFFECTS: no rewriting unrelated docs.
