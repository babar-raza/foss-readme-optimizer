# Upstream issues — Aspose.Font FOSS for Python

Verified: 2026-08-02 against https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python

## Unconstrained [mcp] extra version pin breaks a runtime import
- **Severity**: INFORMATIONAL
- **Evidence**: `pyproject.toml`'s `[mcp]` extra pins `mcp>=1.0` with no upper bound, which resolves to `mcp==2.0.0` today — a version that removed `mcp.server.fastmcp` (renamed to `mcp.server.mcpserver`), breaking `aspose_font/mcp.py`'s import at runtime for anyone who installs the `[mcp]` extra.
- **Impact**: confirmed this does NOT affect any block actually documented in this README (no example imports `aspose_font.mcp`, and the documented dev workflow installs `.[dev]` only, which is unaffected) — it only bites a user who separately installs `.[mcp]` and tries to use the MCP server.
- **Not fixable here because**: the unconstrained version pin is in the upstream `pyproject.toml`.
