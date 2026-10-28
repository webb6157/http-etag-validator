# HTTP ETag Validator

Parses and compares HTTP `ETag` and `If-None-Match` headers, handling weak validators, quoted strings, and comma-separated lists. Standard library only.

```python
from http_etag_validator import ETag, parse_etag, parse_if_none_match, if_none_match_matches

tag = parse_etag('W/"abc123"')      # ETag(value='abc123', weak=True)
tokens = parse_if_none_match('"a", W/"b", "c"')
# ['"a"', 'W/"b"', '"c"']

not_modified = if_none_match_matches('"abc"', 'W/"abc"')
# True — If-None-Match uses weak comparison
```

## Why this exists

Server code that returns `304 Not Modified` tends to either skip the weak/strong distinction or hand-roll a fragile `etag.strip('"W/')` that mangles values containing those characters. This library implements the RFC 9110 §8.8.3 evaluation directly: every tag in `If-None-Match` is compared against the response `ETag` using weak comparison, the wildcard `*` matches any present ETag, and malformed tokens are skipped rather than crashing the request.

The deliberate scope cut: this module only implements `If-None-Match` semantics. It does not implement `If-Match`, which uses strong comparison and has different wildcard behaviour. If you need `If-Match`, do not repurpose `if_none_match_matches` — the comparison rules are wrong for it.

## Edge you will hit

The opaque-tag content is treated as opaque bytes (within the allowed ASCII range). `parse_etag` does not strip whitespace from inside the quotes: `"a b"` and `"ab"` are different tags. If your upstream generates tags with interior whitespace and you expected them trimmed, you will need to normalise before calling `parse_etag`.

Empty quoted strings (`""`) are accepted as valid tags with an empty `value`. This follows the RFC grammar (`DQUOTE *etagc DQUOTE`). If your application never emits empty tags, treat an empty `value` as you would any other unexpected input.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

## Limitations

Values are coerced to floats, so very large integers lose precision. If you need
exact integer aggregates over a window, this is the wrong tool.

## Contributing

Issues and pull requests are welcome. Please keep the dependency list empty —
that constraint is the point of the project, not an oversight.

