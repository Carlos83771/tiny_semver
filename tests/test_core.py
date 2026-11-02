import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tiny_semver import (  # noqa: E402
    InvalidVersion,
    SemVer,
    compare,
    parse,
    sort_versions,
)


class ParseTests(unittest.TestCase):
    def test_parses_core_only(self):
        v = parse("1.2.3")
        self.assertEqual(v.core, (1, 2, 3))
        self.assertEqual(v.prerelease, ())
        self.assertFalse(v.is_prerelease)
        self.assertEqual(str(v), "1.2.3")

    def test_parses_prerelease(self):
        v = parse("1.2.3-alpha.1")
        self.assertEqual(v.core, (1, 2, 3))
        self.assertEqual(v.prerelease, ("alpha", "1"))
        self.assertTrue(v.is_prerelease)

    def test_numeric_prerelease_identifiers_are_not_normalised(self):
        # "1" stays a string in the stored tuple; only ordering converts it.
        v = parse("1.0.0-1.2")
        self.assertEqual(v.prerelease, ("1", "2"))

    def test_build_metadata_is_discarded(self):
        v = parse("1.2.3+build.5")
        self.assertEqual(str(v), "1.2.3")
        self.assertEqual(v, parse("1.2.3"))

    def test_build_metadata_with_prerelease_is_discarded(self):
        v = parse("1.2.3-rc.1+exp.sha.5114f85")
        self.assertEqual(str(v), "1.2.3-rc.1")

    def test_surrounding_whitespace_is_tolerated(self):
        self.assertEqual(parse("  1.2.3  "), parse("1.2.3"))

    def test_rejects_leading_zeros(self):
        for bad in ("01.2.3", "1.02.3", "1.2.03", "1.2.3-01"):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidVersion):
                    parse(bad)

    def test_rejects_malformed(self):
        for bad in (
            "1.2",
            "1.2.3.4",
            "1.2.x",
            "",
            "v1.2.3",
            "1.2.3-",
            "1.2.3-.",
            "1.2.3-alpha..1",
            "1.2.3-alpha_1",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidVersion):
                    parse(bad)

    def test_rejects_non_string(self):
        with self.assertRaises(InvalidVersion):
            parse(1.23)  # type: ignore[arg-type]

    def test_constructor_rejects_bad_prerelease(self):
        with self.assertRaises(InvalidVersion):
            SemVer(1, 2, 3, ("01",))
        with self.assertRaises(InvalidVersion):
            SemVer(1, 2, 3, ("",))
        with self.assertRaises(InvalidVersion):
            SemVer(-1, 2, 3)


class CompareTests(unittest.TestCase):
    def test_core_ordering(self):
        self.assertLess(parse("1.2.3"), parse("1.2.4"))
        self.assertLess(parse("1.2.3"), parse("1.3.0"))
        self.assertLess(parse("1.2.3"), parse("2.0.0"))

    def test_release_outranks_prerelease(self):
        self.assertGreater(parse("1.0.0"), parse("1.0.0-rc.1"))
        self.assertLess(parse("1.0.0-rc.1"), parse("1.0.0"))

    def test_numeric_identifiers_compare_numerically(self):
        self.assertLess(parse("1.0.0-alpha.2"), parse("1.0.0-alpha.10"))

    def test_numeric_sorts_before_alphanumeric(self):
        self.assertLess(parse("1.0.0-1"), parse("1.0.0-alpha"))

    def test_alphanumeric_uses_ascii_order(self):
        self.assertLess(parse("1.0.0-alpha"), parse("1.0.0-beta"))
        self.assertLess(parse("1.0.0-Alpha"), parse("1.0.0-alpha"))

    def test_shorter_prerelease_is_smaller_when_prefix_matches(self):
        self.assertLess(parse("1.0.0-alpha"), parse("1.0.0-alpha.1"))

    def test_compare_returns_int(self):
        self.assertEqual(compare("1.0.0", "1.0.0"), 0)
        self.assertEqual(compare("1.0.0", "1.0.1"), -1)
        self.assertEqual(compare("1.0.1", "1.0.0"), 1)
        self.assertIsInstance(compare("1.0.0", "1.0.0"), int)

    def test_compare_accepts_semver_objects(self):
        self.assertEqual(compare(parse("1.0.0"), "1.0.0"), 0)

    def test_equality_and_hash(self):
        self.assertEqual(parse("1.2.3"), parse("1.2.3"))
        self.assertEqual(hash(parse("1.2.3")), hash(parse("1.2.3")))
        self.assertNotEqual(parse("1.2.3"), parse("1.2.3-rc.1"))

    def test_comparison_with_incompatible_type_raises(self):
        with self.assertRaises(TypeError):
            parse("1.2.3") < 5  # type: ignore[operator]


class SortTests(unittest.TestCase):
    def test_sorts_mixed_input(self):
        raw = [
            "1.0.0",
            "1.0.0-rc.1",
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "0.9.9",
            "1.0.0-beta.11",
            "1.0.0-beta.2",
        ]
        got = [str(v) for v in sort_versions(raw)]
        self.assertEqual(
            got,
            [
                "0.9.9",
                "1.0.0-alpha",
                "1.0.0-alpha.1",
                "1.0.0-beta.2",
                "1.0.0-beta.11",
                "1.0.0-rc.1",
                "1.0.0",
            ],
        )

    def test_accepts_semver_objects(self):
        got = sort_versions([parse("2.0.0"), parse("1.0.0")])
        self.assertEqual([str(v) for v in got], ["1.0.0", "2.0.0"])
        self.assertTrue(all(isinstance(v, SemVer) for v in got))

    def test_does_not_mutate_input(self):
        raw = ["2.0.0", "1.0.0"]
        sort_versions(raw)
        self.assertEqual(raw, ["2.0.0", "1.0.0"])

    def test_empty_input(self):
        self.assertEqual(sort_versions([]), [])


if __name__ == "__main__":
    unittest.main()
