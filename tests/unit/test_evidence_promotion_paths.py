import hashlib

import pytest

from readme_agent.evidence.promotion_paths import (
    compact_readme_path,
    enumerate_readmes,
    migrate_preserved_entry,
    remove_preserved_entry,
)


def _item(content: bytes, committed_readme: str) -> dict:
    return {
        "repository": "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
        "platform": "java",
        "source_revision": "a" * 40,
        "candidate_sha256": hashlib.sha256(content).hexdigest(),
        "committed_readme": committed_readme,
        "verdict": "NO_OP_PROVEN",
    }


def test_migrates_preserved_readme_to_compact_checksum_bound_path(tmp_path):
    repo_root = tmp_path / "repo"
    output_root = repo_root / "evidence"
    old_relative = "evidence/repositories/java/old/revision/hash/README.md"
    old_path = repo_root / old_relative
    old_path.parent.mkdir(parents=True)
    content = b"# Verified README\n"
    old_path.write_bytes(content)

    migrated = migrate_preserved_entry(
        _item(content, old_relative),
        repo_root=repo_root,
        output_root=output_root,
        read_committed_file=lambda _path: pytest.fail("filesystem bytes should be available"),
    )

    expected = output_root / compact_readme_path(
        "aspose-cells-foss/x", "java", "a" * 40, migrated["candidate_sha256"]
    )
    assert expected.read_bytes() == content
    assert migrated["committed_readme"] == expected.relative_to(repo_root).as_posix()
    assert not old_path.exists()
    assert enumerate_readmes(output_root / "repositories") == {expected.resolve()}


def test_uses_committed_bytes_when_long_source_is_not_readable(tmp_path):
    repo_root = tmp_path / "repo"
    output_root = repo_root / "evidence"
    old_relative = "evidence/repositories/net/missing/README.md"
    content = b"# Preserved from Git\n"

    migrated = migrate_preserved_entry(
        _item(content, old_relative) | {"platform": "net"},
        repo_root=repo_root,
        output_root=output_root,
        read_committed_file=lambda path: content if path.as_posix() == old_relative else b"",
    )

    assert (repo_root / migrated["committed_readme"]).read_bytes() == content


def test_rejects_wrong_committed_bytes_before_writing_destination(tmp_path):
    repo_root = tmp_path / "repo"
    output_root = repo_root / "evidence"
    old_relative = "evidence/repositories/net/missing/README.md"
    content = b"# Expected\n"

    with pytest.raises(ValueError, match="preserved README hash mismatch"):
        migrate_preserved_entry(
            _item(content, old_relative) | {"platform": "net"},
            repo_root=repo_root,
            output_root=output_root,
            read_committed_file=lambda _path: b"# Wrong\n",
        )

    destination = output_root / compact_readme_path(
        "aspose-cells-foss/x",
        "net",
        "a" * 40,
        hashlib.sha256(content).hexdigest(),
    )
    assert not destination.exists()


def test_removes_checksum_verified_superseded_readme(tmp_path):
    repo_root = tmp_path / "repo"
    output_root = repo_root / "evidence"
    old_relative = "evidence/repositories/java/old/README.md"
    old_path = repo_root / old_relative
    old_path.parent.mkdir(parents=True)
    content = b"# Superseded\n"
    old_path.write_bytes(content)

    remove_preserved_entry(
        _item(content, old_relative),
        repo_root=repo_root,
        output_root=output_root,
        read_committed_file=lambda _path: pytest.fail("filesystem bytes should be available"),
    )

    assert not old_path.exists()


def test_enumeration_propagates_unreadable_subtree(tmp_path, monkeypatch):
    def failing_walk(*_args, **kwargs):
        kwargs["onerror"](OSError("unreadable promoted subtree"))
        return iter(())

    monkeypatch.setattr("readme_agent.evidence.file_inventory.os.walk", failing_walk)

    with pytest.raises(OSError, match="unreadable promoted subtree"):
        enumerate_readmes(tmp_path)


def test_enumeration_requires_the_canonical_root_to_exist(tmp_path):
    with pytest.raises(FileNotFoundError):
        enumerate_readmes(tmp_path / "repositories")
