"""Verify comment-only source-example equivalence across supported ecosystems."""

from readme_agent.readme.source_claim_example_equivalence import (
    source_claim_has_comments,
    verified_comment_free_example,
)


def test_go_comment_only_example_matches_verified_compiled_payload() -> None:
    verified = 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("ready")\n}\n'
    source = (
        "```go\n"
        'package main\n\nimport "fmt"\n\nfunc main() {\n'
        "\t// Report the verified result.\n"
        '\tfmt.Println("ready")\n}\n'
        "```"
    )

    transformed = verified_comment_free_example(source, verified)

    assert source_claim_has_comments(source)
    assert transformed is not None
    assert "Report the verified result" not in transformed
    assert 'fmt.Println("ready")' in transformed


def test_go_comment_cleanup_rejects_a_changed_operation() -> None:
    verified = 'package main\n\nfunc main() {\n\tprintln("ready")\n}\n'
    changed = (
        "```go\npackage main\n\nfunc main() {\n"
        "\t// This comment is removable, but the operation is not.\n"
        '\tprintln("different")\n}\n```'
    )

    assert verified_comment_free_example(changed, verified) is None


def test_uncommented_go_example_is_recognized_without_false_comment_detection() -> None:
    code = 'package main\n\nfunc main() {\n\tprintln("ready")\n}\n'
    fence = f"```go\n{code}```"

    assert not source_claim_has_comments(fence)
    assert verified_comment_free_example(fence, code) == fence
