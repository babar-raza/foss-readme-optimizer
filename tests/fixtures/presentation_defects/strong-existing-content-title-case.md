# Acme Mesh Toolkit

Acme Mesh Toolkit is a Rust library for validating triangular meshes and exporting verified
geometry to OBJ files.

## In This README

- [Install](#install)
- [Example](#example)
- [Known Limitations](#known-limitations)
- [License](#license)

## Install

Build the crate from this repository with the pinned Rust toolchain.

## Example

```rust
use acme_mesh::Mesh;

let mesh = Mesh::triangle();
mesh.write_obj("triangle.obj")?;
```

## Known Limitations

Only triangular faces are accepted.

## License

MIT
