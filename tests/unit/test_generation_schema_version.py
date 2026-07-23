"""Version tripwire (Consistency & Determinism Tier 1 SS4): prompts.py or
renderer.py's owned-span contract changed without bumping
facts.GENERATION_SCHEMA_VERSION. Fails closed on a purely cosmetic edit too --
that's the intended, deliberately annoying-sometimes behavior, not a bug.

To bump: edit the file, bump GENERATION_SCHEMA_VERSION in facts.py, then
regenerate the snapshot json with the new hashes and version.
"""

import hashlib
import json
from pathlib import Path

from readme_agent.readme.facts import GENERATION_SCHEMA_VERSION

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "generation_schema_version_snapshot.json"
)
WATCHED_FILES = {
    "prompts_py": REPO_ROOT / "src" / "readme_agent" / "llm" / "prompts.py",
    "renderer_py": REPO_ROOT / "src" / "readme_agent" / "readme" / "renderer.py",
}


def _sha256_file(path: Path) -> str:
    # Git may materialize the same tracked blob with LF or CRLF depending on checkout settings.
    # The contract is the Python source text, not a workstation's line-ending policy.
    with path.open("r", encoding="utf-8", newline=None) as source:
        normalized = source.read()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def test_contract_hash_is_checkout_line_ending_invariant(tmp_path):
    lf = tmp_path / "lf.py"
    crlf = tmp_path / "crlf.py"
    lf.write_bytes(b"first = 1\nsecond = 2\n")
    crlf.write_bytes(b"first = 1\r\nsecond = 2\r\n")

    assert _sha256_file(lf) == _sha256_file(crlf)


def test_owned_span_contract_files_changed_only_with_a_version_bump():
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    current_hashes = {name: _sha256_file(path) for name, path in WATCHED_FILES.items()}
    files_changed = current_hashes != snapshot["hashes"]
    version_bumped = GENERATION_SCHEMA_VERSION != snapshot["generation_schema_version"]

    if files_changed and not version_bumped:
        raise AssertionError(
            "prompts.py and/or renderer.py changed without bumping "
            "GENERATION_SCHEMA_VERSION in facts.py. If this is a real "
            "contract change, bump the version and regenerate "
            f"{SNAPSHOT_PATH} with the new hashes and version. If it's a "
            "purely cosmetic edit, this failing is the intended, "
            "fail-closed behavior -- bump anyway."
        )
