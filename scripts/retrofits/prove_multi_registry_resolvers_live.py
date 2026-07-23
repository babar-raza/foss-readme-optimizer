"""Wave 11.2 (`PKG-001`-`004`) live proof: every new `ecosystems/
resolver.py` registry (PyPI, npm, NuGet, the Go module proxy, Conan
Center, vcpkg) checked against a real known-good package and a real
known-empty (deliberately nonexistent) name, live, over the real network
-- not assumed from documentation. Matches the same methodology
`test_ecosystem_resolver.py::TestResolveJava`'s own comment already cites
for Maven Central (`plans/investigations/full-registry-portfolio-survey.md`
finding D-2): a real registry response, not a mocked one, is what actually
proves a resolver's URL/status-code shape is correct.

Kept after use as the executable record of this verification -- see
plans/GOVERNANCE.md, "Repository layout", placement rule 5.
"""

from readme_agent.ecosystems import resolver

_CASES: list[tuple[str, dict[str, str], bool]] = [
    ("python", {"name": "requests"}, True),
    ("python", {"name": "this-package-should-not-exist-zzz-12345"}, False),
    ("typescript", {"name": "lodash"}, True),
    ("typescript", {"name": "this-package-should-not-exist-zzz-12345"}, False),
    ("net", {"name": "Newtonsoft.Json"}, True),
    ("net", {"name": "this-package-should-not-exist-zzz-12345"}, False),
    ("go", {"name": "github.com/pkg/errors"}, True),
    ("go", {"name": "github.com/this/should-not-exist-zzz-12345"}, False),
    ("cpp_conan", {"name": "zlib"}, True),
    ("cpp_conan", {"name": "this-should-not-exist-zzz-12345"}, False),
    ("cpp_vcpkg", {"name": "zlib"}, True),
    ("cpp_vcpkg", {"name": "this-should-not-exist-zzz-12345"}, False),
]


def main() -> int:
    all_ok = True
    for ecosystem, manifest, expected in _CASES:
        result = resolver.resolve(ecosystem, manifest)
        ok = result.found == expected
        all_ok &= ok
        status = "OK " if ok else "FAIL"
        print(f"{status} {ecosystem:12s} {manifest} -> found={result.found} ({result.detail})")
    print()
    print("ALL LIVE CHECKS PASSED" if all_ok else "SOME LIVE CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
