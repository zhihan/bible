import unittest

import add_verses


class TestUtils(unittest.TestCase):
    def test_remove_trailing_punctuation(self):
        self.assertEqual(
            add_verses.remove_trailing_punctuation("Hello, world!"), "Hello, world"
        )
        self.assertEqual(
            add_verses.remove_trailing_punctuation("Hello, world:"), "Hello, world"
        )

    def test_is_reference(self):
        self.assertTrue(add_verses.is_reference("John 3:16"))
        self.assertTrue(add_verses.is_reference("John 3:16 "))
        self.assertTrue(add_verses.is_reference("1 John 3:16-18"))
        self.assertTrue(add_verses.is_reference("John 3:16, 18"))
        self.assertTrue(add_verses.is_reference("John 3:16-18, 20"))
        self.assertTrue(add_verses.is_reference("John 3:16-18, 20-22"))
        self.assertTrue(add_verses.is_reference("Matt. 3:16-18, 20-22"))
        self.assertTrue(add_verses.is_reference("cf. Matt. 3:16-18, 20-22"))
        self.assertTrue(add_verses.is_reference("11:12"))  # Use last book
        self.assertTrue(add_verses.is_reference("11"))  # Use last book and chapter
        self.assertTrue(add_verses.is_reference("vv. 16-18, 20-22"))
        self.assertTrue(add_verses.is_reference("v. 11"))
        self.assertTrue(add_verses.is_reference("vv. 16, 18"))
        self.assertTrue(add_verses.is_reference("Matt. 3:16-18, footnote 1"))

    def test_is_reference_false(self):
        self.assertFalse(add_verses.is_reference("John3:16-18"))
        self.assertFalse(add_verses.is_reference("Some-wordWithHyphens"))

    def test_find_dash_before_reference(self):
        line = "The Lord is the word of God. - John 1:1"
        self.assertEqual(add_verses.find_dash_before_reference(line), 29)

        line = "The Lord is the word of God. - v. 1; Psa. 1:1"
        self.assertEqual(add_verses.find_dash_before_reference(line), 29)

        line = "The Lord is the word of God. - no references"
        self.assertIsNone(add_verses.find_dash_before_reference(line))

        line = "The Lord is the word of God. - v. 1; some other text"
        self.assertIsNone(add_verses.find_dash_before_reference(line))

    def test_find_references_in_paren(self):
        line = "The Lord is the word of God (John 1:1-2)."
        self.assertEqual(add_verses.find_references_in_paren(line), ["John 1:1-2"])

    def test_find_references_in_paren_false(self):
        line = "The Lord is the word of God (no reference)."
        self.assertEqual(add_verses.find_references_in_paren(line), [])
