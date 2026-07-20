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


class TestResolveDispatch:
    def test_unregistered_ecosystem_fails_without_a_network_call(self):
        result = resolver.resolve("pypi", {"name": "aspose-cells-foss"})
        assert not result.found
        assert "no live resolver registered" in result.detail
