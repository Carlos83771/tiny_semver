# tiny_semver

Parse, compare and sort semantic versions, including prereleases, with no dependencies beyond the standard library.

```python
from tiny_semver import parse, compare, sort_versions

v = parse("1.2.3-rc.1")
v.major, v.minor, v.patch   # (1, 2, 3)
v.prerelease                # ('rc', '1')
v.is_prerelease             # True
str(v)                      # '1.2.3-rc.1'

compare("1.0.0-alpha", "1.0.0")            # -1
compare("1.0.0-alpha.2", "1.0.0-alpha.10") # -1

[str(x) for x in sort_versions(["1.0.0", "1.0.0-rc.1", "0.9.9"])]
# ['0.9.9', '1.0.0-rc.1', '1.0.0']
```

## Why this exists

Most version-comparison helpers either accept anything that looks vaguely like a version or drag in a full parser for every ecosystem's flavour. This library does neither: it accepts a strict subset of SemVer 2.0.0 and rejects everything else with `InvalidVersion`. The trade-off is that build metadata (`+build.5`) is recognised on input but thrown away, because build metadata is explicitly excluded from precedence in the specification and keeping it would complicate equality. If you need the original string with its build suffix, keep it yourself; `SemVer` will not round-trip it.

## The awkward edge

Prerelease ordering is the part that trips people up, and it is the one place where a library can quietly disagree with the spec. The rules applied here are the specification's rules, in full:

- A release outranks any prerelease of the same core: `1.0.0 > 1.0.0-rc.1`.
- Numeric identifiers compare numerically, so `1.0.0-alpha.2 < 1.0.0-alpha.10`.
- A numeric identifier always sorts before an alphanumeric one: `1.0.0-1 < 1.0.0-alpha`.
- A shorter prerelease that is a prefix of a longer one sorts first: `1.0.0-alpha < 1.0.0-alpha.1`.

Leading zeros are rejected everywhere they are illegal (`01.2.3`, `1.2.3-01`), and surrounding whitespace is stripped before parsing.

## API

- `parse(text) -> SemVer` — parse a string, raising `InvalidVersion` on failure.
- `SemVer.parse(text)` — the same thing as a classmethod.
- `SemVer(major, minor, patch, prerelease=())` — construct directly; `prerelease` is a sequence of identifier strings.
- `compare(left, right) -> int` — `-1`, `0` or `1`; each argument may be a `SemVer` or a string.
- `sort_versions(iterable) -> list[SemVer]` — ascending precedence, returning a new list of `SemVer` objects.
- `SemVer` supports `==`, `<`, `<=`, `>`, `>=`, `hash()`, `str()` and `repr()`, and exposes `major`, `minor`, `patch`, `prerelease`, `core` and `is_prerelease`.
- `InvalidVersion` is a subclass of `ValueError`.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

