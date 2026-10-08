# json-path — Build Notes

**Week 48** | Seeded and built 2026-10-04

## What it does

Query JSON with a simple dotted/bracket path expression. One stdlib Python file, no dependencies. Replaces the constant `python -c 'import json,sys; print(json.load(open("f"))["key"])'` one-liner pattern.

## Design decisions

**Navigation only, no query language.** The scope boundary is deliberate: `.users[0].name` and `.items[*].price` cover 90% of real usage. Filters (`select`, `map`), pipes, and arithmetic are jq territory. Scope creep here would mean reimplementing jq badly. The tool's one-sentence pitch is "get one value out of this JSON without learning jq" — anything that complicates that sentence is out.

**Wildcard `[*]` expands on both arrays and objects.** Arrays return items in order. Objects return values (not keys). This is a deliberate choice: when you want all prices from an array of objects, you write `.items[*].price` and it works. If you want keys, use jq.

**Multi-match output is one result per line.** This makes `[*]` pipeline-friendly: `json-path -r .tags[*] package.json | sort | uniq`. No JSON array wrapping unless you pipe through `jq -s` to collect.

**Flags before positionals.** argparse has a known quirk: when you have two positionals (path and file) and optional flags, interleaving flags between them (`json-path .name -r file.json`) causes argparse to lose the second positional. Convention: flags come first, like jq (`jq -r .filter file.json`). Documented plainly.

**Raw mode on scalars.** `-r` strips JSON encoding from strings, booleans, nulls, and numbers. Objects and arrays still print as JSON (indented). This matches jq's `-r` behavior: "I want the string value, not the JSON representation of the string."

**Exit code 2 for bad input.** Path syntax errors and JSON parse errors are caller mistakes, not data absences. Exit 1 is reserved for "path exists but has no value here" (key missing, index OOB) so scripts can distinguish "bad query" from "data doesn't have this field."

**`--null-on-missing` for safe scripting.** Sometimes you want `null` output for a missing key rather than a non-zero exit — e.g., piping into another tool that handles null. This opt-in keeps the default behavior strict (exit 1) while not requiring callers to always handle exits.

**Stdlib only.** `json`, `re`, `argparse`, `sys`, `subprocess` (not used), `pathlib` (not used). Works anywhere Python 3.6+ runs without a venv.

## Test coverage

55 tests across: parse_path unit tests, identity path, key access (simple, nested, missing, wrong type), array access (index, negative, out-of-range, wrong type), wildcard (array, object, nested, wrong type), raw output (all scalar types + objects + multivalue), stdin input, compact flag, error cases (missing file, invalid JSON, invalid path, quiet mode), bracket key notation, scalar root, integration tests.

Tests spin real temp files (no mocking). Path parsing tested via importlib module loading so parse_path is exercised directly, not just through subprocess.

## What's blocked

Release needs `GH_TOKEN`. Tool is complete; waiting on re-auth.

## Lessons

The argparse two-positionals-plus-flags issue is subtle and worth knowing: flags MUST precede positionals when both are present. jq has this same constraint and documents it the same way. The fix is not to hack argparse but to match convention and document it.

The `.` identity path (empty segments list) makes `json-path . file.json` a pleasant alternative to `python -m json.tool file.json` — it pretty-prints with 2-space indent and gives clear error messages on malformed JSON.
