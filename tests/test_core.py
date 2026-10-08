import unittest

from http_etag_validator import (
    ETag,
    parse_etag,
    parse_if_none_match,
    if_none_match_matches,
)


class ParseETagTests(unittest.TestCase):
    def test_strong_quoted(self):
        result = parse_etag('"abc123"')
        self.assertIsNotNone(result)
        self.assertEqual(result.value, "abc123")
        self.assertFalse(result.weak)

    def test_weak_prefix(self):
        result = parse_etag('W/"abc123"')
        self.assertIsNotNone(result)
        self.assertEqual(result.value, "abc123")
        self.assertTrue(result.weak)

    def test_empty_header_returns_none(self):
        self.assertIsNone(parse_etag(""))
        self.assertIsNone(parse_etag("   "))

    def test_missing_quotes_returns_none(self):
        self.assertIsNone(parse_etag("abc123"))
        self.assertIsNone(parse_etag('"abc123'))
        self.assertIsNone(parse_etag('abc123"'))

    def test_empty_quoted_string_invalid(self):
        # An opaque-tag must contain at least zero chars, but etagc excludes
        # DQUOTE. The empty quoted string "" is structurally valid per the
        # grammar (DQUOTE *etagc DQUOTE), so we accept it.
        result = parse_etag('""')
        self.assertIsNotNone(result)
        self.assertEqual(result.value, "")

    def test_lowercase_w_not_weak(self):
        # The weak indicator is case-sensitive: W/ only.
        self.assertIsNone(parse_etag('w/"abc"'))

    def test_control_character_rejected(self):
        # An interior space (0x20) is below the etagc range (0x21, 0x23-7E)
        # and must be rejected. The opaque-tag content is opaque bytes within
        # the allowed ASCII range; the literal backslash in 'ab\tcd' is a
        # valid etagc character (0x5C), so that token is accepted.
        self.assertIsNone(parse_etag('"ab cd"'))

    def test_all_valid_etagc_accepted(self):
        # Every printable ASCII except DQUOTE is allowed inside the quotes.
        chars = "".join(chr(c) for c in range(0x21, 0x7F) if c != 0x22)
        result = parse_etag('"' + chars + '"')
        self.assertIsNotNone(result)
        self.assertEqual(result.value, chars)

    def test_whitespace_around_token_trimmed(self):
        result = parse_etag('  "abc"  ')
        self.assertIsNotNone(result)
        self.assertEqual(result.value, "abc")

    def test_whitespace_between_weak_and_quote_rejected(self):
        # RFC 9110 §8.8.4 grammar: entity-tag = [ weak ] opaque-tag, where
        # weak = %x57.2F ("W/") is a single token with no optional whitespace
        # between it and the opaque-tag. 'W/ "abc"' is therefore malformed.
        result = parse_etag('W/ "abc"')
        self.assertIsNone(result)


class ParseIfNoneMatchTests(unittest.TestCase):
    def test_single_tag(self):
        self.assertEqual(parse_if_none_match('"abc"'), ['"abc"'])

    def test_multiple_tags(self):
        tokens = parse_if_none_match('"a", W/"b", "c"')
        self.assertEqual(tokens, ['"a"', 'W/"b"', '"c"'])

    def test_wildcard(self):
        self.assertEqual(parse_if_none_match("*"), ["*"])

    def test_empty_header(self):
        self.assertEqual(parse_if_none_match(""), [])
        self.assertEqual(parse_if_none_match("   "), [])

    def test_empty_tokens_dropped(self):
        self.assertEqual(parse_if_none_match('"a", , "b"'), ['"a"', '"b"'])

    def test_whitespace_around_tokens_trimmed(self):
        tokens = parse_if_none_match('  "a"  ,  W/"b"  ')
        self.assertEqual(tokens, ['"a"', 'W/"b"'])


class IfNoneMatchMatchesTests(unittest.TestCase):
    def test_strong_matches_strong(self):
        self.assertTrue(if_none_match_matches('"abc"', '"abc"'))

    def test_weak_candidate_matches_strong_current(self):
        # If-None-Match uses weak comparison, so a weak validator in the
        # request matches a strong validator in the response.
        self.assertTrue(if_none_match_matches('W/"abc"', '"abc"'))

    def test_strong_candidate_matches_weak_current(self):
        self.assertTrue(if_none_match_matches('"abc"', 'W/"abc"'))

    def test_weak_candidate_matches_weak_current(self):
        self.assertTrue(if_none_match_matches('W/"abc"', 'W/"abc"'))

    def test_different_values_no_match(self):
        self.assertFalse(if_none_match_matches('"abc"', '"def"'))

    def test_wildcard_matches_any_etag(self):
        self.assertTrue(if_none_match_matches('*', '"anything"'))
        self.assertTrue(if_none_match_matches('*', 'W/"anything"'))

    def test_wildcard_does_not_match_missing_etag(self):
        # * means "any representation exists". No ETag means none exists.
        self.assertFalse(if_none_match_matches('*', ''))

    def test_one_of_several_matches(self):
        self.assertTrue(
            if_none_match_matches('"a", "b", "c"', '"b"')
        )

    def test_none_of_several_matches(self):
        self.assertFalse(
            if_none_match_matches('"a", "b"', '"c"')
        )

    def test_weak_in_list_matches(self):
        self.assertTrue(
            if_none_match_matches('"a", W/"b", "c"', '"b"')
        )

    def test_empty_if_none_match_no_match(self):
        self.assertFalse(if_none_match_matches('', '"abc"'))

    def test_missing_etag_no_match(self):
        self.assertFalse(if_none_match_matches('"abc"', ''))

    def test_malformed_token_in_list_skipped(self):
        # A malformed token is not a match, but does not invalidate the rest.
        self.assertTrue(
            if_none_match_matches('broken, "abc"', '"abc"')
        )

    def test_all_malformed_tokens_no_match(self):
        self.assertFalse(
            if_none_match_matches('broken, also-broken', '"abc"')
        )


class ETagDataclassTests(unittest.TestCase):
    def test_equality(self):
        self.assertEqual(ETag("abc", False), ETag("abc", False))
        self.assertNotEqual(ETag("abc", False), ETag("abc", True))

    def test_frozen(self):
        tag = ETag("abc", False)
        with self.assertRaises(Exception):
            tag.value = "xyz"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
