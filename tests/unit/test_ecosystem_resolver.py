from readme_agent.ecosystems import resolver


class FakeResponse:
    def __init__(self, num_found: int, status_code: int = 200):
        self._num_found = num_found
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise resolver.requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return {"response": {"numFound": self._num_found}}


class TestResolveJava:
    def test_found(self, monkeypatch):
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: FakeResponse(num_found=1))
        result = resolver.resolve("java", {"group_id": "org.aspose", "artifact_id": "aspose-pdf"})
        assert result.found
        assert "found" in result.detail

    def test_not_found_matches_the_real_cells_java_finding(self, monkeypatch):
        """Real evidence this test is modeled on: org.aspose:aspose-cells-foss
        returns zero results on Maven Central (verified live, 2026-07-18,
        plans/investigations/full-registry-portfolio-survey.md finding D-2)."""
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: FakeResponse(num_found=0))
        result = resolver.resolve(
            "java", {"group_id": "org.aspose", "artifact_id": "aspose-cells-foss"}
        )
        assert not result.found
        assert "NOT FOUND" in result.detail

    def test_missing_coordinates_fails_without_a_network_call(self, monkeypatch):
        def fail_if_called(*a, **k):
            raise AssertionError("must not call the network with no coordinates")

        monkeypatch.setattr(resolver.requests, "get", fail_if_called)
        result = resolver.resolve("java", {})
        assert not result.found
        assert "group_id" in result.detail

    def test_network_error_is_reported_not_raised(self, monkeypatch):
        def raise_error(*a, **k):
            raise resolver.requests.ConnectionError("dns failure")

        monkeypatch.setattr(resolver.requests, "get", raise_error)
        result = resolver.resolve("java", {"group_id": "org.aspose", "artifact_id": "x"})
        assert not result.found
        assert "dns failure" in result.detail

    def test_network_error_sets_blocked_true(self, monkeypatch):
        """`PKG-005`: a real network failure must be distinguishable from a
        genuine "not found" -- `blocked=True` is how a caller tells them
        apart."""

        def raise_error(*a, **k):
            raise resolver.requests.ConnectionError("dns failure")

        monkeypatch.setattr(resolver.requests, "get", raise_error)
        result = resolver.resolve("java", {"group_id": "org.aspose", "artifact_id": "x"})
        assert result.blocked

    def test_genuine_not_found_does_not_set_blocked(self, monkeypatch):
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: FakeResponse(num_found=0))
        result = resolver.resolve("java", {"group_id": "org.aspose", "artifact_id": "x"})
        assert not result.blocked


class TestResolveDispatch:
    def test_unregistered_ecosystem_fails_without_a_network_call(self):
        result = resolver.resolve("pypi", {"name": "aspose-cells-foss"})
        assert not result.found
        assert "no live resolver registered" in result.detail


class _StatusResponse:
    """Generic 200/404 fake -- every resolver below except Maven's own
    richer JSON-query shape resolves purely from the status code."""

    def __init__(self, status_code: int):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise resolver.requests.HTTPError(f"HTTP {self.status_code}")


class TestResolvePypi:
    def test_found(self, monkeypatch):
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: _StatusResponse(200))
        result = resolver.resolve("python", {"name": "requests"})
        assert result.found
        assert "PyPI" in result.detail

    def test_not_found(self, monkeypatch):
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: _StatusResponse(404))
        result = resolver.resolve("python", {"name": "this-should-not-exist-zzz"})
        assert not result.found
        assert "NOT FOUND" in result.detail
        assert not result.blocked

    def test_network_error_sets_blocked_true(self, monkeypatch):
        def raise_error(*a, **k):
            raise resolver.requests.ConnectionError("dns failure")

        monkeypatch.setattr(resolver.requests, "get", raise_error)
        result = resolver.resolve("python", {"name": "requests"})
        assert not result.found
        assert result.blocked

    def test_missing_name_fails_without_a_network_call(self, monkeypatch):
        def fail_if_called(*a, **k):
            raise AssertionError("must not call the network with no name")

        monkeypatch.setattr(resolver.requests, "get", fail_if_called)
        result = resolver.resolve("python", {})
        assert not result.found


class TestResolveNpm:
    def test_found(self, monkeypatch):
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: _StatusResponse(200))
        result = resolver.resolve("typescript", {"name": "lodash"})
        assert result.found
        assert "npm" in result.detail

    def test_not_found(self, monkeypatch):
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: _StatusResponse(404))
        result = resolver.resolve("typescript", {"name": "this-should-not-exist-zzz"})
        assert not result.found


class TestResolveNuget:
    def test_found(self, monkeypatch):
        captured_urls = []

        def fake_get(url, *a, **k):
            captured_urls.append(url)
            return _StatusResponse(200)

        monkeypatch.setattr(resolver.requests, "get", fake_get)
        result = resolver.resolve("net", {"name": "Newtonsoft.Json"})
        assert result.found
        assert captured_urls[0].endswith("newtonsoft.json/index.json")  # lowercased

    def test_not_found(self, monkeypatch):
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: _StatusResponse(404))
        result = resolver.resolve("net", {"name": "This-Should-Not-Exist-Zzz"})
        assert not result.found


class TestResolveGoProxy:
    def test_found(self, monkeypatch):
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: _StatusResponse(200))
        result = resolver.resolve("go", {"name": "github.com/pkg/errors"})
        assert result.found
        assert "Go proxy" in result.detail

    def test_not_found(self, monkeypatch):
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: _StatusResponse(404))
        result = resolver.resolve("go", {"name": "github.com/this/should-not-exist-zzz"})
        assert not result.found

    def test_uppercase_module_path_is_escaped(self):
        assert resolver._escape_go_module_path("github.com/PuerkitoBio/goquery") == (
            "github.com/!puerkito!bio/goquery"
        )

    def test_already_lowercase_path_is_unchanged(self):
        assert resolver._escape_go_module_path("github.com/pkg/errors") == "github.com/pkg/errors"

    def test_module_path_is_escaped_before_the_request(self, monkeypatch):
        captured_urls = []

        def fake_get(url, *a, **k):
            captured_urls.append(url)
            return _StatusResponse(200)

        monkeypatch.setattr(resolver.requests, "get", fake_get)
        resolver.resolve("go", {"name": "github.com/PuerkitoBio/goquery"})
        assert "!puerkito!bio" in captured_urls[0]


class TestResolveConan:
    def test_found(self, monkeypatch):
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: _StatusResponse(200))
        result = resolver.resolve("cpp_conan", {"name": "zlib"})
        assert result.found
        assert "Conan Center" in result.detail

    def test_not_found(self, monkeypatch):
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: _StatusResponse(404))
        result = resolver.resolve("cpp_conan", {"name": "this-should-not-exist-zzz"})
        assert not result.found

    def test_falls_back_to_library_target_when_name_absent(self, monkeypatch):
        captured_urls = []

        def fake_get(url, *a, **k):
            captured_urls.append(url)
            return _StatusResponse(200)

        monkeypatch.setattr(resolver.requests, "get", fake_get)
        result = resolver.resolve("cpp_conan", {"library_target": "zlib"})
        assert result.found
        assert "zlib" in captured_urls[0]


class TestResolveVcpkg:
    def test_found(self, monkeypatch):
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: _StatusResponse(200))
        result = resolver.resolve("cpp_vcpkg", {"name": "zlib"})
        assert result.found
        assert "vcpkg" in result.detail

    def test_not_found(self, monkeypatch):
        monkeypatch.setattr(resolver.requests, "get", lambda *a, **k: _StatusResponse(404))
        result = resolver.resolve("cpp_vcpkg", {"name": "this-should-not-exist-zzz"})
        assert not result.found

    def test_no_direct_cpp_key_exists(self):
        """`cpp` deliberately has no single resolved registry -- a caller
        must choose `cpp_conan`/`cpp_vcpkg` explicitly, never an ambiguous
        guess (this module's own docstring states why)."""
        result = resolver.resolve("cpp", {"name": "zlib"})
        assert not result.found
        assert "no live resolver registered" in result.detail
