# psyche-test-select

WHEN TO USE: choosing the inner-loop test subset for a change.

INPUTS: affected files from `psyche-impact`.

STEPS:
1. Select tests that reference the touched modules (targeted, not the whole suite).
2. Map to pytest markers where possible: `unit`, `integration`, `security`, `contracts`.
3. Run the smallest set that covers a named realistic failure.

OUTPUT: the targeted pytest command(s).

STOP CONDITIONS: never run the full suite after every edit; the final risk gate runs
once. Do not skip a test just to go faster.

ALLOWED TOOLS: Grep, rg, pytest (targeted).

FORBIDDEN SIDE EFFECTS: no `-x`/skip/xfail to fake green; no marker removal.
