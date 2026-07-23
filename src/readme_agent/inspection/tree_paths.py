"""Git-tree-API-based manifest path detection (decision #40/Part F,
`SCL-004`) -- the no-checkout counterpart to `file_inventory.py`'s
`os.walk()`-based `_find_manifest_paths()`. `github_api.client.get_tree()`
lists every path in a repo at a given commit in one call, no clone; this
module answers the same "which manifest is where" question from that flat
path list instead of a real working tree, sharing the exact same matching
rule (`file_inventory.resolve_manifest_candidates()`) so a glob added to
`ecosystems.registry` is honored identically by both traversal strategies.
"""

import fnmatch

from readme_agent.ecosystems.registry import known_manifest_globs
from readme_agent.inspection.file_inventory import NOISE_DIRS, resolve_manifest_candidates


def _is_noise_path(path: str) -> bool:
    """True if any directory component of a repo-relative path is a noise
    directory -- same `NOISE_DIRS` set `_find_manifest_paths()` prunes
    `os.walk()` with, applied here as a filter over the tree API's already-
    complete flat listing instead of a traversal-time skip."""
    parts = path.split("/")[:-1]
    return any(part in NOISE_DIRS for part in parts)


def find_manifest_paths_from_tree(tree_entries: list[dict]) -> dict[str, str]:
    """`tree_entries` is `get_tree()`'s own `response["tree"]` list
    (`{"path": ..., "type": "blob"|"tree", ...}`, GitHub's git-tree-API
    shape) -- blob entries under a noise directory are excluded, `tree`
    (directory) entries are never candidates themselves. Returns one
    repo-relative path string per detected ecosystem, mirroring
    `_find_manifest_paths()`'s return shape exactly except for `Path` vs
    `str` (no working tree exists to root a `Path` in)."""
    candidates = (
        (entry["path"].rsplit("/", 1)[-1], entry["path"])
        for entry in tree_entries
        if entry.get("type") == "blob" and not _is_noise_path(entry["path"])
    )
    return resolve_manifest_candidates(candidates)


def find_all_manifest_roots_from_tree(tree_entries: list[dict]) -> list[tuple[str, str]]:
    """Wave 11.1 (`ECO-004`): the git-tree-API counterpart to
    `file_inventory.py::find_all_manifest_roots()` -- every manifest match
    across the whole tree, not just the first per ecosystem. Shares the
    same glob-matching rule and noise-path exclusion as
    `find_manifest_paths_from_tree()` above; deliberately a separate
    function, not a change to it, for the same additive-not-replacing
    reason `find_all_manifest_roots()` is its own function alongside
    `_find_manifest_paths()`."""
    globs = known_manifest_globs()
    found: list[tuple[str, str]] = []
    for entry in tree_entries:
        if entry.get("type") != "blob" or _is_noise_path(entry["path"]):
            continue
        filename = entry["path"].rsplit("/", 1)[-1]
        for ecosystem, patterns in globs.items():
            if any(fnmatch.fnmatch(filename, pattern) for pattern in patterns):
                found.append((ecosystem, entry["path"]))
    return found
