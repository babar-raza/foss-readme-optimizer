# Aspose.PDF FOSS for Java

> Pure Java PDF library, zero third-party dependencies

[![Build Status](https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Java/actions/workflows/build.yml/badge.svg)](https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Java/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Maven Central](https://img.shields.io/maven-central/v/org.aspose/aspose-pdf.svg)](https://search.maven.org/artifact/org.aspose/aspose-pdf)
[![Java Version](https://img.shields.io/badge/Java-11%2B-blue.svg)](https://openjdk.org/projects/jdk/11/)

Aspose.PDF FOSS for Java is an open-source Java library for working with PDF documents. It is API-compatible with [Aspose.PDF for Java](https://products.aspose.com/pdf/java/), targets ISO 32000-1:2008 compliance, and depends only on the standard Java platform — no third-party libraries required.

## Status

**Version 26.7** (Aspose-style year.month versioning). The library is functional for many common workflows but breaking changes may still happen between releases. See the [roadmap](#status--roadmap) below for current coverage.

## Features

- **Text** — extraction, search, and replacement with `TextFragmentAbsorber` and `TextAbsorber`; RTL/Arabic shaping
- **Document generation** — pages, paragraphs, tables (`Table`/`Row`/`Cell`), floating boxes, headers/footers, text/image/page-number stamps, watermarks
- **Drawing API** — graphs and shapes (`Line`, `Rectangle`, `Circle`, `Arc`, `Curve`, `Ellipse`), gradient shadings
- **Images** — extraction from PDF pages; rasterization of pages to PNG, JPEG, GIF, BMP, TIFF; multi-frame TIFF import
- **Forms** — AcroForm support: text fields, checkboxes, radio buttons, combo boxes, list boxes, signature fields
- **XFA forms** — fill and read XFA data, JavaScript and FormCalc scripting, rendering, conversion to AcroForm, flattening
- **Annotations** — text markup (highlight, underline, strikeout, squiggly), free text, ink, stamps, file attachments, links, redaction
- **Bookmarks & Outlines** — read, modify, and create document outline trees
- **Digital Signatures** — PKCS#7 signing (RSA, DSA, ECDSA) and signature verification
- **Encryption** — AES-128/256, RC4-40/128; password protection (user/owner)
- **Optimization** — `Document.optimizeResources()`: unused-object removal, duplicate-stream linking, stream recompression, image compression/downsampling, font subsetting
- **PDF/A** — validation and conversion to PDF/A-1, PDF/A-2, PDF/A-3, PDF/A-4
- **HTML** — HTML-to-PDF import (`HtmlLoadOptions`) and save to HTML/XML
- **XMP Metadata** — read and write document metadata
- **Page operations** — split, merge, rotate, resize content, reorder
- **Layers (OCG)** — read and write optional content groups
- **Attachments** — embedded files collection, preserved across merges
- **Document structure** — tagged PDF, logical structure
- **Facades** — `PdfFileEditor`, `PdfContentEditor`, `PdfBookmarkEditor`, `PdfExtractor`, `PdfConverter`, `PdfFileSignature`, and more
- **Zero dependencies** — uses only `java.*`, `javax.crypto`, `javax.imageio`, `javax.xml.*`

## Installation

Maven Central publication is planned but the artifact is **not yet available** on Central. For now, build from source:

```bash
git clone https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Java.git
cd Aspose.PDF-FOSS-for-Java
mvn clean install
```

Once on Maven Central, add to your `pom.xml`:

```xml
<dependency>
    <groupId>org.aspose</groupId>
    <artifactId>aspose-pdf</artifactId>
    <version>26.7</version>
</dependency>
```

Gradle:

```groovy
implementation 'org.aspose:aspose-pdf:26.7'
```

## Quick Start

### Extract text from an existing PDF

```java
import org.aspose.pdf.Document;
import org.aspose.pdf.text.TextAbsorber;

try (Document doc = new Document("input.pdf")) {
    TextAbsorber absorber = new TextAbsorber();
    doc.getPages().accept(absorber);
    String text = absorber.getText();
    System.out.println(text);
}
```

### Extract images from a PDF

```java
import org.aspose.pdf.Document;
import org.aspose.pdf.XImage;

import java.io.FileOutputStream;

try (Document doc = new Document("input.pdf")) {
    int pageIndex = 1;
    int imageIndex = 1;
    for (XImage image : doc.getPages().get(pageIndex).getResources().getImages()) {
        try (FileOutputStream out = new FileOutputStream("image-" + imageIndex + ".png")) {
            image.save(out);
        }
        imageIndex++;
    }
}
```

### Create a PDF from scratch

```java
import org.aspose.pdf.Document;
import org.aspose.pdf.Page;
import org.aspose.pdf.text.TextFragment;

try (Document doc = new Document()) {
    Page page = doc.getPages().add();
    TextFragment fragment = new TextFragment("Hello, PDF world!");
    page.getParagraphs().add(fragment);
    doc.save("output.pdf");
}
```

### Work with forms

```java
import org.aspose.pdf.Document;
import org.aspose.pdf.forms.Form;
import org.aspose.pdf.forms.TextBoxField;

try (Document doc = new Document("form.pdf")) {
    Form form = doc.getForm();
    TextBoxField nameField = (TextBoxField) form.get("name");
    nameField.setValue("Jane Doe");

    // Iterate all fields
    for (org.aspose.pdf.forms.Field field : form.getFields()) {
        System.out.println(field.getPartialName() + " = " + field.getValue());
    }

    doc.save("form-filled.pdf");
}
```

## Documentation

API documentation will be published at https://aspose-pdf-foss.github.io/Aspose.PDF-FOSS-for-Java/ once a stable release is tagged. For now, JavaDoc can be generated locally:

```bash
mvn javadoc:javadoc
```

The generated HTML lives in `target/site/apidocs/`.

## Status & Roadmap

This is an early-stage open-source effort. The following coverage matrix tracks parity against the commercial Aspose.PDF for Java API:

| Area | Status |
|---|---|
| Document model (COS layer, pages, resources) | ✅ Implemented |
| Text extraction, search, replacement | ✅ Implemented |
| Image extraction and page rasterization | ✅ Implemented |
| Document generation (paragraphs, tables, stamps, headers/footers) | ✅ Implemented |
| Drawing API (shapes, gradients) | ✅ Implemented |
| AcroForm fields | ✅ Implemented |
| XFA forms (fill, JavaScript/FormCalc, rendering, conversion to AcroForm, flattening) | ✅ Implemented |
| Annotations | ✅ Implemented (most types, incl. redaction) |
| Bookmarks & outlines | ✅ Implemented |
| Digital signatures (PKCS#7: RSA/DSA/ECDSA) | ✅ Implemented |
| Encryption (AES, RC4) | ✅ Implemented |
| Resource optimization (`optimizeResources`: dedup, recompression, image downsampling, font subsetting) | ✅ Implemented |
| PDF/A validation & conversion | ✅ Implemented |
| HTML to PDF | ✅ Implemented |
| Layers (optional content groups) | ✅ Implemented |
| Attachments / embedded files | ✅ Implemented |
| Facades (`PdfFileEditor`, `PdfContentEditor`, ...) | ✅ Implemented |
| XMP metadata | ✅ Implemented |
| Tagged PDF / logical structure | 🟡 Partial |

Bug reports and feature requests are welcome via [GitHub Issues](https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Java/issues).

## Contributing

Pull requests are welcome. Before opening one, please:

1. Open an issue describing the change you intend to make
2. Ensure `mvn test` passes locally
3. Follow the existing code style (run `mvn checkstyle:check` if configured)
4. Keep changes focused — one PR per logical change
5. Do not add third-party runtime dependencies; this is a zero-dependency library

See [AGENTS.md](AGENTS.md) for additional guidance, particularly if you are using an AI coding assistant.

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for the full text.

## Related projects

[Aspose.PDF for Java](https://products.aspose.com/pdf/java/) is a commercial library from Aspose Pty Ltd that offers a broader feature set, including OCR and conversion to many non-PDF formats. The FOSS edition shares the same API shape, so user code can often migrate between the two with minimal changes.
