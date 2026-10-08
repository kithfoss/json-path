#!/usr/bin/env python3
"""json-path — query JSON with a dotted/bracket path expression.

Usage:
    json-path '.users[0].name' data.json
    cat data.json | json-path '.users[0].name'
    json-path '.items[*].price' data.json
    json-path '.' data.json          # identity (pretty-print whole document)
"""

import argparse
import json
import re
import sys


def parse_path(expr):
    """Parse a path expression into a list of segments.

    Returns a list of:
        ('key', str)       — .name
        ('index', int)     — [0], [-1]
        ('wildcard', None) — [*]
    Raises ValueError on malformed input.
    """
    if not expr or expr == '.':
        return []

    if not expr.startswith('.') and not expr.startswith('['):
        raise ValueError(f"Path must start with '.' or '[': {expr!r}")

    segments = []
    i = 0

    while i < len(expr):
        if expr[i] == '.':
            # consume the dot
            i += 1
            if i >= len(expr):
                raise ValueError(f"Trailing dot in path: {expr!r}")
            if expr[i] == '[':
                # .[0] syntax — bracket handler picks it up next iteration
                continue
            # read key: letters, digits, underscore, dollar, hyphen
            m = re.match(r'([A-Za-z_$][A-Za-z0-9_$-]*)', expr[i:])
            if not m:
                raise ValueError(f"Invalid key at position {i} in path: {expr!r}")
            segments.append(('key', m.group(1)))
            i += len(m.group(1))
        elif expr[i] == '[':
            end = expr.find(']', i)
            if end == -1:
                raise ValueError(f"Unclosed '[' at position {i} in path: {expr!r}")
            inner = expr[i+1:end]
            if inner == '*':
                segments.append(('wildcard', None))
            else:
                try:
                    segments.append(('index', int(inner)))
                except ValueError:
                    # could be ["key"] or ['key'] syntax
                    if (inner.startswith('"') and inner.endswith('"')) or \
                       (inner.startswith("'") and inner.endswith("'")):
                        segments.append(('key', inner[1:-1]))
                    else:
                        raise ValueError(f"Invalid bracket content {inner!r} in path: {expr!r}")
            i = end + 1
        else:
            raise ValueError(f"Unexpected character {expr[i]!r} at position {i} in path: {expr!r}")

    return segments


def apply_segment(data, segment, path_so_far):
    """Apply one segment to data. Returns a list of results (wildcard may expand)."""
    kind, val = segment

    if kind == 'key':
        if not isinstance(data, dict):
            raise LookupError(
                f"Cannot access key {val!r} on {type(data).__name__} at {path_so_far!r}"
            )
        if val not in data:
            raise LookupError(f"Key {val!r} not found at {path_so_far!r}")
        return [data[val]]

    elif kind == 'index':
        if not isinstance(data, list):
            raise LookupError(
                f"Cannot index into {type(data).__name__} at {path_so_far!r}"
            )
        try:
            return [data[val]]
        except IndexError:
            raise LookupError(
                f"Index {val} out of range (len={len(data)}) at {path_so_far!r}"
            )

    elif kind == 'wildcard':
        if isinstance(data, list):
            return list(data)
        elif isinstance(data, dict):
            return list(data.values())
        else:
            raise LookupError(
                f"[*] requires array or object, got {type(data).__name__} at {path_so_far!r}"
            )

    else:
        raise ValueError(f"Unknown segment kind: {kind!r}")


def query(data, segments):
    """Walk segments over data, expanding wildcards. Returns list of matches."""
    current = [data]
    for i, seg in enumerate(segments):
        path_so_far = _segments_to_str(segments[:i])
        next_values = []
        for item in current:
            results = apply_segment(item, seg, path_so_far)
            next_values.extend(results)
        current = next_values
    return current


def _segments_to_str(segments):
    parts = []
    for kind, val in segments:
        if kind == 'key':
            parts.append(f'.{val}')
        elif kind == 'index':
            parts.append(f'[{val}]')
        elif kind == 'wildcard':
            parts.append('[*]')
    return ''.join(parts) or '.'


def format_value(value, raw=False):
    """Format a single value for output."""
    if raw and isinstance(value, str):
        return value
    if raw and value is None:
        return 'null'
    if raw and isinstance(value, bool):
        return 'true' if value else 'false'
    if raw and isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        prog='json-path',
        description='Query JSON with a dotted/bracket path expression.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Path syntax:
  .key          access object key
  [N]           array index (negative: [-1] = last)
  [*]           all items in array or object values
  .             identity (root)
  ["key"]       bracket notation for keys with special chars

Examples:
  json-path '.name' data.json
  json-path '.users[0].email' data.json
  json-path '.items[*].price' data.json
  cat data.json | json-path '.meta.version'
  json-path '.' data.json              # pretty-print whole doc
  json-path '.tags[*]' -r data.json    # one string per line, no quotes
""",
    )
    parser.add_argument('path', help='Path expression (e.g. .users[0].name)')
    parser.add_argument(
        'file', nargs='?', help='JSON file (reads stdin if omitted)'
    )
    parser.add_argument(
        '-r', '--raw',
        action='store_true',
        help='Output strings without JSON encoding (no surrounding quotes)',
    )
    parser.add_argument(
        '--null-on-missing',
        action='store_true',
        help='Print null instead of exiting 1 when path not found',
    )
    parser.add_argument(
        '--compact',
        action='store_true',
        help='Compact JSON output (no indentation) for non-scalar results',
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress error messages (still exits 1 on failure)',
    )

    args = parser.parse_args()

    # Load JSON input
    try:
        if args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            if sys.stdin.isatty():
                parser.error('No file given and stdin is a terminal. Pipe JSON or provide a filename.')
            data = json.load(sys.stdin)
    except FileNotFoundError:
        if not args.quiet:
            print(f"json-path: file not found: {args.file}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        if not args.quiet:
            src = args.file or '<stdin>'
            print(f"json-path: invalid JSON in {src}: {e}", file=sys.stderr)
        sys.exit(2)

    # Parse path
    try:
        segments = parse_path(args.path)
    except ValueError as e:
        if not args.quiet:
            print(f"json-path: {e}", file=sys.stderr)
        sys.exit(2)

    # Query
    try:
        matches = query(data, segments)
    except LookupError as e:
        if args.null_on_missing:
            print('null')
            sys.exit(0)
        if not args.quiet:
            print(f"json-path: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    indent = None if args.compact else 2
    for value in matches:
        if isinstance(value, (dict, list)):
            print(json.dumps(value, ensure_ascii=False, indent=indent))
        else:
            print(format_value(value, raw=args.raw))

    sys.exit(0)


if __name__ == '__main__':
    main()
