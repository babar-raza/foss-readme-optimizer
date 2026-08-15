# Upstream issues — Aspose.Cells FOSS for C++

Verified: 2026-08-02 against https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp
(NuGet package findings below re-verified 2026-08-04 by downloading and extracting the real
`Aspose.Cells.Cpp.FOSS` 26.4.1 `.nupkg` from nuget.org)

## ctest requires -C Debug on the default multi-config generator
- **Severity**: INFORMATIONAL
- **Evidence**: plain `cmake ..` with no `-G` selects the multi-config Visual Studio generator on Windows; running bare `ctest` afterward reports "Test not available without configuration" — it requires `ctest -C Debug` (or `-C Release`).
- **Impact**: contributors following a naive `cmake .. && cmake --build . && ctest` sequence hit a confusing test-discovery failure.
- **Not fixable here because**: it's a characteristic of the upstream project's own CMake configuration (not pinning a single-config generator); already worked around in this README (added the `-C Debug` flag).

## NuGet package's bundled sample doesn't exercise its own packaged CMake config
- **Severity**: INFORMATIONAL
- **Evidence**: downloaded and extracted the real `Aspose.Cells.Cpp.FOSS` 26.4.1 `.nupkg` from
  nuget.org. It correctly ships `build/native/Aspose.Cells.Cpp.FOSS/{include/, lib/win_x86{,_64}/
  {Debug,Release}/aspose_cells_foss.lib}` plus a working `aspose.cells.cpp.foss-config.cmake`
  (defines an `Aspose.Cells.Cpp.FOSS` imported target) and MSBuild `.targets` file. But the
  package's own bundled `build/native/samples/CMakeLists.txt` doesn't reference either — it does
  `add_subdirectory("../Aspose.Cells.Foss.Cpp")` against a sibling **source** directory that isn't
  actually present in the package, i.e. the sample as shipped can't build from the package
  contents alone.
- **Impact**: a developer trying to follow the package's own bundled sample to learn the
  CMake-config consumption path will find it doesn't work out of the box; the MSBuild `.targets`
  path (Visual Studio `PackageReference`) is unaffected and works as documented.
- **Not fixable here because**: the sample is bundled inside the published package itself, not
  something a README edit can change; confirmed via direct byte-for-byte inspection of the real
  package's `-config.cmake`/`.targets`/`CMakeLists.txt` contents, not a live compile (no MSVC
  toolchain was available in this verification pass to compile-test the CMake-config consumption
  path end-to-end — TOOLCHAIN-UNAVAILABLE for that specific path; the CMake integration snippet in
  this README's Installation section is derived directly from the real `-config.cmake` file's
  target name and directory layout, not invented).
