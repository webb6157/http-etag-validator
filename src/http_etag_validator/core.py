"""
Core ETag parsing and comparison logic.

Implements RFC 9110 §8.8.3 (If-None-Match) and §8.8.4 (ETag) semantics for the
subset of validators that arise in ordinary server code: quoted opaque-tags,
the optional weak indicator, and the wildcard and comma-separated list forms.

The comparison rules are taken from RFC 9110 §8.8.3.1:

  When If-None-Match is used for a conditional GET, the comparison is *weak*
  for every recipient tag EXCEPT the wildcard. That is the one we implement.
  We do NOT implement the strong-comparison variant used by If-Match, because
  If-Match is a separate header with separate rules and the brief does not ask
  for it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ETag:
    """A single entity-tag.

    Attributes:
        value: The opaque-tag content WITHOUT surrounding quotes. The spec
            calls the wire form a "quoted-string"; we store the unquoted value
            so callers can compare directly without re-trimming.
        weak: True if the tag was prefixed with ``W/``. Weak tags compare equal
            to strong tags of the same value under weak comparison, which is
            the only comparison this module performs.
    """

    value: str
    weak: bool = False


def parse_etag(header: str) -> ETag | None:
    """Parse a single ETag header value into an :class:`ETag`.

    Returns ``None`` when the header is absent or syntactically malformed.
    An empty string (the common "header not provided" case) is treated as
    None rather than raising, so callers can pass ``headers.get("ETag", "")``
    without an extra branch.

    RFC 9110 §8.8.4 grammar::

        entity-tag = [ weak ] opaque-tag
        weak       = %x57.2F            ; "W/", case-sensitive
        opaque-tag = DQUOTE *etagc DQUOTE
        etagc      = %x21 / %x23-7E     ; VCHAR except double quotes

    We accept the full etagc range. We deliberately do NOT strip whitespace
    from inside the quotes: the opaque-tag content is opaque, and changing
    whitespace would change its meaning.
    """
    s = header.strip()
    if not s:
        return None

    weak = False
    if s.startswith("W/"):
        weak = True
        s = s[2:]

    if len(s) < 2 or s[0] != '"' or s[-1] != '"':
        return None

    inner = s[1:-1]
    for i, ch in enumerate(inner):
        code = ord(ch)
        if code == 0x21:
            continue
        if 0x23 <= code <= 0x7E:
            continue
        return None

    return ETag(value=inner, weak=weak)


def parse_if_none_match(header: str) -> list[str]:
    """Parse an If-None-Match header into a list of raw tag tokens.

    Each returned token is exactly the text between commas, with surrounding
    whitespace trimmed — including any ``W/`` prefix and surrounding quotes.
    We return raw tokens rather than :class:`ETag` objects because the
    If-None-Match grammar allows the literal ``*`` wildcard, which is not a
    valid ETag. Keeping the wildcard as a token lets the matcher distinguish
    it from a malformed quoted tag.

    RFC 9110 §8.8.3 grammar::

        If-None-Match = "*" / ( 1#entity-tag )

    Empty tokens between commas (e.g. ``"a", , "b"``) are dropped silently.
    They are technically a protocol error, but per the guidance in §16.2 of
    RFC 9110 we are encouraged to be tolerant of whitespace oddities in
    received header fields.
    """
    s = header.strip()
    if not s:
        return []

    out: list[str] = []
    for raw in s.split(","):
        token = raw.strip()
        if token:
            out.append(token)
    return out


def if_none_match_matches(if_none_match_header: str, etag_header: str) -> bool:
    """Return True if the request should yield a 304 Not Modified.

    This implements the §8.8.3 evaluation: for every tag in If-None-Match, do
    a *weak* comparison against the current response ETag. The wildcard ``*``
    matches any existing resource (i.e. any non-None ETag). If If-None-Match
    is empty, or the response has no ETag, the result is False.

    Weak comparison (§8.8.3.2) treats two tags as matching when their opaque
    values are bytewise equal, regardless of either tag's weak/strong flag.
    This is the correct rule for If-None-Match on GET; it is NOT the rule for
    If-Match, which this module does not implement.
    """
    tokens = parse_if_none_match(if_none_match_header)
    if not tokens:
        return False

    current = parse_etag(etag_header)
    if current is None:
        return False

    for token in tokens:
        if token == "*":
            return True
        candidate = parse_etag(token)
        if candidate is None:
            continue
        if candidate.value == current.value:
            return True

    return False
