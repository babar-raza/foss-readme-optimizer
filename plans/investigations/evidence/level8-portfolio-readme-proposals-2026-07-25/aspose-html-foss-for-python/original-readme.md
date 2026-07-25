# Aspose.HTML FOSS for Python

Aspose.HTML FOSS for Python is an open-source Python toolkit for working with HTML documents and DOM trees.

It is focused on practical HTML parsing, DOM inspection and mutation, serialization, URL handling, and early CSS-oriented document workflows in a lightweight Python package.

## Features

- Parse HTML strings, bytes, fragments, and files into a DOM document
- Inspect and manipulate DOM nodes, elements, attributes, text, comments, and document fragments
- Use familiar DOM APIs such as `Document`, `Element`, `NodeList`, `HTMLCollection`, `DOMParser`, and `XMLSerializer`
- Work with common HTML element classes and form/table/list/media element surfaces
- Serialize DOM trees back to HTML
- Use WHATWG-style URL and URL search parameter helpers
- Evaluate basic CSS selector matching and CSSOM-style declarations used by DOM workflows

## Installation

```bash
pip install aspose-html-foss
```

## Quick Start

```python
from aspose_html import HTMLDocument, serialise

document = HTMLDocument.parse("""
<!doctype html>
<html>
  <body>
    <main id="content">
      <h1>Hello HTML</h1>
      <p class="lead">Created with Aspose.HTML FOSS for Python.</p>
    </main>
  </body>
</html>
""")

content = document.get_element_by_id("content")
paragraph = document.create_element("p")
paragraph.text_content = "DOM updates are represented in the document tree."
content.append_child(paragraph)

print(serialise(content))
```

## Package Entry Points

- `aspose_html.HTMLDocument`: parse HTML documents, fragments, and files
- `aspose_html.dom.Document`: DOM document root and node factory
- `aspose_html.dom.Element`: element node API for attributes, traversal, and mutation
- `aspose_html.dom.DOMParser`: parse markup through a DOM-style parser entry point
- `aspose_html.dom.XMLSerializer`: serialize DOM nodes through a DOM-style serializer entry point
- `aspose_html.serialise`: serialize nodes to HTML strings
- `aspose_html.URL`: WHATWG-style URL object
- `aspose_html.URLSearchParams`: URL query parameter helper

## Compatibility

Main supported scenarios:

- Parse HTML into a document tree
- Create and update DOM nodes programmatically
- Query documents by ID, tag name, class name, and selector-oriented helpers
- Read and write element attributes, classes, datasets, inline styles, and text content
- Serialize complete documents, fragments, and individual elements
- Work with URL parsing and search parameters
- Exercise CSS/CSSOM primitives used by document and style workflows

API layers:

- High-level HTML API: `aspose_html.HTMLDocument`
- DOM API: `aspose_html.dom`, centered around `Document`, `Element`, `Node`, and HTML element classes
- Serialization API: `aspose_html.serialise`
- URL API: `aspose_html.url`, centered around `URL` and `URLSearchParams`
- CSS/CSSOM API: `aspose_html.css` and `aspose_html.cssom`

For the stable API summary, see [PUBLIC_API.md](PUBLIC_API.md). For runnable scenarios, see [examples](examples).

## Examples

### Parse And Read HTML

```python
from aspose_html import HTMLDocument

document = HTMLDocument.parse("<article><h1>News</h1><p>Hello</p></article>")
heading = document.get_elements_by_tag_name("h1").item(0)

print(heading.text_content)
```

### Create DOM Nodes

```python
from aspose_html.dom import Document
from aspose_html import serialise

document = Document()
section = document.create_element("section")
section.set_attribute("class", "card")
section.text_content = "Generated content"

document.append_child(section)
print(serialise(document))
```

### Work With URLs

```python
from aspose_html import URL

url = URL("https://example.com/articles?id=10")
url.search_params.set("page", "2")

print(str(url))
```

## Links

- Repository: [https://github.com/aspose-html-foss/Aspose.HTML-FOSS-for-Python](https://github.com/aspose-html-foss/Aspose.HTML-FOSS-for-Python)
- Issues: [https://github.com/aspose-html-foss/Aspose.HTML-FOSS-for-Python/issues](https://github.com/aspose-html-foss/Aspose.HTML-FOSS-for-Python/issues)
- PyPI: [https://pypi.org/project/aspose-html-foss/](https://pypi.org/project/aspose-html-foss/)

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
