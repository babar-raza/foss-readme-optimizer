"""Prove that unbound Aspose URLs are removed without discarding visitor text."""

from readme_agent.links.occurrences import find_aspose_link_occurrences
from readme_agent.readme.document_link_hygiene import remove_unbound_aspose_links


def test_every_supported_url_form_is_unwrapped_without_duplicate_rewrites() -> None:
    source = """## Resources

[Documentation](https://docs.aspose.org/cells/python/)
![Product diagram](https://products.aspose.com/cells/)
<https://kb.aspose.org/cells/python/example/>
<a href="https://reference.aspose.com/cells/python-net/">API reference</a>
Raw: https://blog.aspose.com/cells/example/
"""

    candidate, rewrites = remove_unbound_aspose_links(source)

    assert [rewrite.form for rewrite in rewrites] == [
        "markdown",
        "image",
        "autolink",
        "html",
        "raw",
    ]
    assert not find_aspose_link_occurrences(candidate)
    assert "Documentation" in candidate
    assert "Product diagram" in candidate
    assert "API reference" in candidate


def test_non_aspose_links_and_comment_like_text_are_byte_identical() -> None:
    source = (
        "[Project guide](https://example.org/guide)\n"
        "`https://example.org/code`\n"
        "<!-- a visitor comment, governed by the separate comment contract -->\n"
    )

    candidate, rewrites = remove_unbound_aspose_links(source)

    assert candidate == source
    assert rewrites == []


def test_urls_inside_fenced_and_inline_code_are_never_rewritten() -> None:
    source = """## Example

```python
endpoint = "https://api.aspose.com/example"
```

Use `https://docs.aspose.org/example/` as a literal fixture.
"""

    candidate, rewrites = remove_unbound_aspose_links(source)

    assert candidate == source
    assert rewrites == []
