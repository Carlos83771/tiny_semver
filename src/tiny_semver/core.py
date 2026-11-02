"""Core semantic version parsing and comparison.

This module implements a deliberate subset of the SemVer 2.0.0 specification:

* Versions are ``MAJOR.MINOR.PATCH`` (all non-negative integers, no leading
  zeros) optionally followed by a prerelease ``-PRERELEASE``.
* Build metadata (``+BUILD``) is *recognised on input but discarded*. It is not
  part of the parsed value and never participates in comparison. This is the
  single interpretation this library commits to; callers that need to retain
  build metadata should keep the original string.
* Prerelease identifiers are dot-separated. Numeric identifiers compare
  numerically; alphanumeric identifiers compare with the usual ASCII ordering.
  A numeric identifier always has lower precedence than an alphanumeric one,
  per the specification.
* A version without a prerelease has higher precedence than the same version
  with one.
"""

from __future__ import annotations

import re
from functools import total_ordering
from typing import Iterable, List, Sequence, Tuple, Union

__all__ = ["SemVer", "InvalidVersion", "parse", "compare", "sort_versions"]


class InvalidVersion(ValueError):
    """Raised when a string cannot be parsed as a semantic version."""


# Leading zeros are forbidden on the numeric core and on numeric prerelease
# identifiers. `[0-9]+` would accept them, so the alternation is explicit.
_NUM = r"(?:0|[1-9][0-9]*)"
_NUM_OR_ALPHA = r"[0-9A-Za-z-]+"
_PRERELEASE = r"(?:%s)(?:\.(?:%s))*" % (_NUM_OR_ALPHA, _NUM_OR_ALPHA)
_BUILD = r"[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*"

_VERSION_RE = re.compile(
    r"^"
    r"(?P<major>%s)\.(?P<minor>%s)\.(?P<patch>%s)"
    r"(?:-(?P<prerelease>%s))?"
    r"(?:\+(?P<build>%s))?"
    r"$" % (_NUM, _NUM, _NUM, _PRERELEASE, _BUILD)
)


def _identifier_key(identifier: str) -> Tuple[int, int, Union[int, str]]:
    """Return a sort key for one prerelease identifier.

    Numeric identifiers sort before alphanumeric ones, so the first element of
    the tuple is 0 for numeric and 1 for alphanumeric. Numeric identifiers are
    compared by value; alphanumeric ones by their raw string. The middle field
    is unused for numeric identifiers and exists only to keep the tuple shape
    uniform.
    """
    if identifier.isdigit():
        return (0, int(identifier), "")
    return (1, 0, identifier)


@total_ordering
class SemVer:
    """An immutable parsed semantic version.

    ``SemVer`` compares with other ``SemVer`` instances and with strings; the
    string is parsed on demand so that ``SemVer("1.2.3") < "1.2.4"`` works.
    Comparing against anything else raises ``TypeError``.
    """

    __slots__ = ("major", "minor", "patch", "prerelease", "_text")

    def __init__(
        self,
        major: int,
        minor: int,
        patch: int,
        prerelease: Sequence[str] = (),
    ) -> None:
        if major < 0 or minor < 0 or patch < 0:
            raise InvalidVersion("version components must be non-negative")
        self.major = int(major)
        self.minor = int(minor)
        self.patch = int(patch)
        self.prerelease: Tuple[str, ...] = tuple(str(p) for p in prerelease)
        for identifier in self.prerelease:
            if not identifier or not re.fullmatch(_NUM_OR_ALPHA, identifier):
                raise InvalidVersion("invalid prerelease identifier: %r" % (identifier,))
            if identifier.isdigit() and len(identifier) > 1 and identifier[0] == "0":
                raise InvalidVersion("numeric prerelease identifier has a leading zero")
        self._text = self._render()

    def _render(self) -> str:
        text = "%d.%d.%d" % (self.major, self.minor, self.patch)
        if self.prerelease:
            text += "-" + ".".join(self.prerelease)
        return text

    @classmethod
    def parse(cls, text: str) -> "SemVer":
        """Parse ``text`` into a ``SemVer`` or raise ``InvalidVersion``."""
        if not isinstance(text, str):
            raise InvalidVersion("version must be a string, got %s" % type(text).__name__)
        match = _VERSION_RE.match(text.strip())
        if match is None:
            raise InvalidVersion("invalid semantic version: %r" % (text,))
        prerelease = match.group("prerelease")
        identifiers = prerelease.split(".") if prerelease else ()
        return cls(
            int(match.group("major")),
            int(match.group("minor")),
            int(match.group("patch")),
            identifiers,
        )

    @property
    def core(self) -> Tuple[int, int, int]:
        """The ``(major, minor, patch)`` triple."""
        return (self.major, self.minor, self.patch)

    @property
    def is_prerelease(self) -> bool:
        """True when this version carries at least one prerelease identifier."""
        return bool(self.prerelease)

    def _precedence_key(self):
        """Key used for ordering.

        A release (no prerelease) outranks any prerelease of the same core, so
        the first element is 1 for releases and 0 for prereleases. The second
        element is the tuple of identifier keys.
        """
        if not self.prerelease:
            return (1, ())
        return (0, tuple(_identifier_key(p) for p in self.prerelease))

    def _coerce(self, other) -> "SemVer":
        if isinstance(other, SemVer):
            return other
        if isinstance(other, str):
            return SemVer.parse(other)
        return NotImplemented

    def __eq__(self, other) -> bool:
        coerced = self._coerce(other)
        if coerced is NotImplemented:
            return NotImplemented
        return self.core == coerced.core and self.prerelease == coerced.prerelease

    def __lt__(self, other) -> bool:
        coerced = self._coerce(other)
        if coerced is NotImplemented:
            return NotImplemented
        if self.core != coerced.core:
            return self.core < coerced.core
        return self._precedence_key() < coerced._precedence_key()

    def __hash__(self) -> int:
        return hash((self.core, self.prerelease))

    def __str__(self) -> str:
        return self._text

    def __repr__(self) -> str:
        return "SemVer(%r)" % (self._text,)


def parse(text: str) -> SemVer:
    """Parse ``text`` into a ``SemVer``. Convenience wrapper for ``SemVer.parse``."""
    return SemVer.parse(text)


def compare(left: Union[SemVer, str], right: Union[SemVer, str]) -> int:
    """Return -1, 0 or 1 for ``left`` less than, equal to, or greater than ``right``."""
    a = left if isinstance(left, SemVer) else SemVer.parse(left)
    b = right if isinstance(right, SemVer) else SemVer.parse(right)
    if a < b:
        return -1
    if b < a:
        return 1
    return 0


def sort_versions(versions: Iterable[Union[SemVer, str]]) -> List[SemVer]:
    """Return the versions sorted by ascending precedence.

    Accepts an iterable of ``SemVer`` or strings and always returns a new list
    of ``SemVer``. The input is not mutated.
    """
    parsed = [v if isinstance(v, SemVer) else SemVer.parse(v) for v in versions]
    parsed.sort()
    return parsed
