"""Git-tree-API-based manifest path detection (decision #40/Part F,
`SCL-004`) -- the no-checkout counterpart to `file_inventory.py`'s
`os.walk()`-based `_find_manifest_paths()`. `github_api.client.get_tree()`
lists every path in a repo at a given commit in one call, no clone; this
module answers the same "which manifest is where" question from that flat
path list instead of a real working tree, sharing the exact same matching
rule (`file_inventory.resolve_manifest_candidates()`) so a glob added to
`ecosystems.registry` is honored identically by both traversal strategies.
"""

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
