<!-- readme-agent:presentation hash="sha256:c95f627a411cc22b5a93fe27c51245a92d39565d3da3cd80f895d6bae1766d86" schema="3" inner-bytes="5339" -->
# Aspose.3D FOSS for Java

A free and open-source implementation of Aspose.3D for Java, released under the permissive **MIT License**. It provides an API-compatible, open-source alternative for working with 3D scenes and models in Java, maintaining the `com.aspose.threed.*` package structure of the commercial library.

## At a glance

- **For:** Java developers building 3D import, export, and scene-processing applications.
- **Problem solved:** Create, load, inspect, transform, and save 3D scenes with an open-source Java API.
- **Verified capabilities:** Create, load, inspect, transform, and save 3D scenes. Model scene geometry and materials through mesh and material APIs.
- **Verified formats:** Import and export glTF and GLB scenes. Import and export binary and ASCII STL scenes. Import and export Collada scenes.
- **Runtime:** Java 21+
- **Current verified limitation:** Rendering and full commercial-API parity remain incomplete.

## In this README

- [About Aspose.3D FOSS](#about-aspose3d-foss)
- [Project Status](#project-status)
- [API Compatibility](#api-compatibility)
- [Building](#building)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Resources](#resources)
- [Acknowledgments](#acknowledgments)

## Installation

Build the verified repository revision from source:

```bash
git clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Java.git
cd Aspose.3D-FOSS-for-Java
git checkout 605f67d1192fee1881078dfd53d37b8cb29623ba
mvn clean install
```

This path requires JDK 21+ and Maven. The source build and the minimal example
below were verified together at revision `605f67d1192fee1881078dfd53d37b8cb29623ba`.

## About Aspose.3D FOSS

Aspose.3D FOSS is the free, open-source edition of Aspose.3D. It shares the same public API design as the commercial Aspose.3D On-Premise library, so you can:

- **Build and ship 3D applications at no cost** under a permissive MIT License.
- **Start free and grow without rewriting code** — code written against the FOSS edition works with the commercial edition.
- **Upgrade only when you need to** — when you require the broader feature set, higher performance, rendering, or proprietary format support of the [commercial On-Premise edition](https://products.aspose.com/3d/java/), simply swap in the commercial package, no API rewrites required.

The FOSS edition focuses on the most widely used open 3D formats. The commercial edition additionally covers proprietary and high-performance scenarios such as rendering, advanced mesh operations, and formats like USD, PDF, A3DW, JT, and more.

## Project Status

This is a work-in-progress port. See [TODO.md](TODO.md) for current progress and [FILE_FORMATS.md](FILE_FORMATS.md) for format support status.

## API Compatibility

The public API matches Aspose.3D for Java 26.1.0:
- Package structure: `com.aspose.threed.*`
- Method signatures: Identical to Aspose.3D
- Class names: Same as Aspose.3D

**Excluded APIs:**
- No licensing, trial, or DRM-related functionality (not applicable to an open-source project)
- Some advanced features have stub implementations

## Building

This is a Maven project. Build and test with:

```bash
# Build the project
mvn clean package

# Run tests
mvn test
```

## Usage

### Minimal verified example

```java
import com.aspose.threed.Scene;

public class ReadmeExample {
    public static void main(String[] args) throws Exception {
        Scene scene = new Scene();
        scene.save("scene.stl");
    }
}
```

This exact example was compiled against the source build at revision `605f67d1192fee1881078dfd53d37b8cb29623ba`.


```java
import com.aspose.threed.Scene;

// Load a 3D file
Scene scene = new Scene("testdata/input/cube.obj");

// Save to another format
scene.save("output.stl");
```

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

## Resources

### Aspose.3D FOSS — free & open source (aspose.org)
- [Aspose.3D FOSS for Java](https://products.aspose.org/3d/java/) — product page
- [Aspose.3D FOSS family](https://products.aspose.org/3d/) — all platforms (Python, .NET, Java, TypeScript)
- [Aspose FOSS documentation](https://docs.aspose.org/) — guides for all open-source libraries
- [Aspose FOSS blog](https://blog.aspose.org/) — tutorials and announcements
- [Java FAQ](https://kb.aspose.org/3d/java/faq/) — frequently asked questions

### Aspose.3D — commercial On-Premise edition (aspose.com)
- [Aspose.3D for Java](https://products.aspose.com/3d/java/) — full-featured commercial edition
- [Aspose.3D product family](https://products.aspose.com/3d) — overview
- [Developer documentation](https://docs.aspose.com/3d/java/) — API guides
- [API reference](https://reference.aspose.com/3d/java/) — complete API documentation
- [Download / free trial](https://releases.aspose.com/3d/java/) — get the commercial package

### Community & support
- [Aspose.3D support forum](https://forum.aspose.com/c/3d/19) — questions and help
- [Free online 3D apps](https://products.aspose.app/3d/) — convert and view 3D files in your browser

## Acknowledgments

This is a clean-room FOSS implementation designed for API compatibility with Aspose.3D for Java.
<!-- readme-agent:presentation:end -->
