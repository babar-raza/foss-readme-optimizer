# Upstream issues — Aspose.3D FOSS for Java

Verified: 2026-08-02 against https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Java

## OBJ loader is a no-op stub in the published Maven artifact
- **Severity**: FUNCTIONAL-DEFECT
- **Evidence**: `javap -p -c com.aspose.threed.FileFormat$ObjLoader` against the real `org.aspose:aspose-3d-foss:26.5.0` jar shows the method body is a bare `return new Scene();`. `Scene.fromFile("cube.obj")` compiles and runs with no exception but produces an empty scene (84-byte, header-only STL when re-saved) — despite the upstream GitHub source tree containing a real OBJ parser implementation (shipped-vs-source drift).
- **Impact**: any user loading a real OBJ file through the published jar silently gets an empty scene, no error.
- **Not fixable here because**: the defect is in the compiled/published library artifact itself, not the README. (The README was updated to demonstrate STL round-tripping instead, which is fully functional.)
