"""
HTTP ETag Validator.

Parses and compares ETag and If-None-Match headers per RFC 9110 §8.8.3/§8.8.4.
Supports weak validators, quoted strings, and comma-separated lists.
"""

from .core import ETag, parse_etag, parse_if_none_match, if_none_match_matches

__all__ = [
    "ETag",
    "parse_etag",
    "parse_if_none_match",
    "if_none_match_matches",
]
