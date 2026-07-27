"""Real Aspose Python installed-consumer proof in the hardened Docker boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.registry.loader import require_listed
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import capture_repository_snapshot

REPRESENTATIVE = Path("runs/baseline/aspose-3d-foss__Aspose.3D-FOSS-for-Python")
ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"


@pytest.mark.live
def test_real_aspose_python_package_installs_and_exposes_selected_public_symbols():
    if not REPRESENTATIVE.is_dir():
        pytest.skip("real Python baseline clone is unavailable")
    entry = require_listed(ORG_REPO)
    snapshot = capture_repository_snapshot(entry, REPRESENTATIVE)
    example = MinimalExamplePolicy(
        language="python",
        class_name="readme_example",
        code=(
            "from aspose.threed import Node, Scene\n\n"
            "scene = Scene()\n"
            'node = Node("README proof")\n'
            "assert scene.root_node is not None\n"
            'assert node.name == "README proof"\n'
            "assert node.child_nodes == []\n"
        ),
        evidence_paths=["aspose/threed/Scene.py", "aspose/threed/Node.py"],
        required_symbols=["Scene", "Node", "Scene.root_node", "Node.child_nodes"],
    )

    verification = verify_local_product_example(snapshot, example)

    assert verification.outcome == "SOURCE_BUILD_VERIFIED", verification
    assert verification.truth_eligible is True
    assert verification.isolated_execution is not None
    assert verification.build.isolation_kind == "isolated_result_projection"
    assert verification.isolated_execution.policy.network_mode == "none"
    assert verification.isolated_execution.cleanup.complete is True
