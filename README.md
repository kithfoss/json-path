# json-path

Query JSON with a simple dotted/bracket path expression. No jq needed.

```
json-path [OPTIONS] PATH [FILE]
cat data.json | json-path [OPTIONS] PATH
```

## Examples

```sh
# Get a value
json-path .name package.json
json-path .users[0].email data.json

# All items from an array
json-path .items[*].price data.json

# Pretty-print the whole document
json-path . data.json

# Raw output — strings without JSON quotes (like jq -r)
json-path -r .version package.json

# Negative index — last element
json-path [-1] data.json

# Bracket notation for keys with special characters
json-path '["my-key"]' data.json

# Piped input
curl -s https://api.example.com/data | json-path .results[0].id

# Fallback to null instead of error
json-path --null-on-missing .optional.key data.json

# Compact output for arrays/objects
json-path --compact .tags data.json
```

## Path syntax

| Syntax      | Meaning                              |
|-------------|--------------------------------------|
| `.`         | Identity (root document)             |
| `.key`      | Object key access                    |
| `.a.b.c`    | Nested key access                    |
| `[N]`       | Array index (0-based)                |
| `[-N]`      | Array index from end (`[-1]` = last) |
| `[*]`       | All items (array) or values (object) |
| `["key"]`   | Bracket key (for keys with `-` etc.) |
| `['key']`   | Same with single quotes              |

## Options

| Flag                | Description                                      |
|---------------------|--------------------------------------------------|
| `-r`, `--raw`       | Output strings without JSON encoding (no quotes) |
| `--null-on-missing` | Print `null` instead of exiting 1 on missing key |
| `--compact`         | Compact JSON output for arrays/objects           |
| `-q`, `--quiet`     | Suppress error messages; still exits non-zero    |

## Exit codes

| Code | Meaning                                  |
|------|------------------------------------------|
| 0    | Success                                  |
| 1    | Path not found (key missing, index OOB)  |
| 2    | Bad input (invalid JSON, invalid path)   |

## Installation

```sh
chmod +x json-path.py
sudo ln -s "$(pwd)/json-path.py" /usr/local/bin/json-path
```

Or copy `json-path.py` anywhere on your PATH.

## Notes

- Stdlib only — no dependencies beyond Python 3.6+
- Flags must come before the path expression: `json-path -r .name file.json`
- Multiple matches (from `[*]`) print one per line
- This is intentionally minimal — navigation only, no filters or functions.
  For complex queries, use `jq`.

## Limitations

- No filter expressions (`.items[] | select(.price > 10)`)
- No pipe operator
- No recursive descent (`..`)
- No multi-path output
