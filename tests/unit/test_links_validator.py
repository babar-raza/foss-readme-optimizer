from readme_agent.links import validator


class TestCheckHttps:
    def test_https_passes(self):
        assert validator.check_https("https://products.aspose.com/3d/java/").ok

    def test_http_fails(self):
        assert not validator.check_https("http://products.aspose.com/3d/java/").ok

    def test_ftp_fails(self):
        assert not validator.check_https("ftp://example.com/file").ok


class TestCheckLiveReachable:
    def test_success_response(self, monkeypatch):
        class FakeResponse:
            status_code = 200

        monkeypatch.setattr(
            validator.requests, "head", lambda url, timeout, allow_redirects: FakeResponse()
        )

        result = validator.check_live_reachable("https://example.com")
        assert result.ok

    def test_network_error_is_a_warning_not_a_crash(self, monkeypatch):
        def raise_error(url, timeout, allow_redirects):
            raise validator.requests.ConnectionError("dns failure")

        monkeypatch.setattr(validator.requests, "head", raise_error)

        result = validator.check_live_reachable("https://nonexistent.example")
        assert not result.ok
        assert "dns failure" in result.detail

    def test_falls_back_to_get_when_head_unsupported(self, monkeypatch):
        class Fake404:
            status_code = 404

        class Fake200:
            status_code = 200

        monkeypatch.setattr(
            validator.requests, "head", lambda url, timeout, allow_redirects: Fake404()
        )
        monkeypatch.setattr(
            validator.requests, "get", lambda url, timeout, allow_redirects: Fake200()
        )

        result = validator.check_live_reachable("https://example.com")
        assert result.ok
