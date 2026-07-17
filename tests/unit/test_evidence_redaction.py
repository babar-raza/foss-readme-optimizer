from readme_agent.evidence.redaction import redact, redact_secret_like_values


class TestPatternRedaction:
    def test_redacts_openai_style_key(self):
        assert "[REDACTED]" in redact_secret_like_values("key=sk-abcdefghij1234567890")

    def test_redacts_github_pat(self):
        assert "[REDACTED]" in redact_secret_like_values("token: ghp_abcdefghij1234567890")

    def test_redacts_github_user_token(self):
        assert "[REDACTED]" in redact_secret_like_values("ghu_abcdefghij1234567890")

    def test_redacts_google_api_key(self):
        assert "[REDACTED]" in redact_secret_like_values("AIzaSyABCDEFGHIJ1234567890abc")

    def test_redacts_bearer_header(self):
        text = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345"
        assert "[REDACTED]" in redact_secret_like_values(text)
        assert "abcdefghijklmnopqrstuvwxyz012345" not in redact_secret_like_values(text)

    def test_redacts_api_key_query_param(self):
        text = "https://example.com/endpoint?api_key=abcdefgh12345678"
        assert "[REDACTED]" in redact_secret_like_values(text)

    def test_leaves_ordinary_text_untouched(self):
        text = "This is a normal sentence about MIT licensing."
        assert redact_secret_like_values(text) == text

    def test_non_string_passthrough(self):
        assert redact_secret_like_values(None) is None  # type: ignore[arg-type]


class TestExactValueRedaction:
    def test_masks_live_secret_value_even_without_matching_a_pattern(self):
        secret = "totally-plain-looking-token-value-123"
        text = f"the key is {secret}"
        assert secret not in redact(text, [secret])

    def test_empty_secret_list_is_a_noop_beyond_pattern_redaction(self):
        text = "nothing secret here"
        assert redact(text, []) == text
