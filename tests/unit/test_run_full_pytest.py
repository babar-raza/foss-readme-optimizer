"""Contracts for the bounded full-suite runner."""

from pathlib import Path

from scripts.governance.run_full_pytest import _pytest_command, _selected_nodes, _sha256_text


def test_selected_inventory_is_sorted_and_excludes_summary_lines():
    output = (
        "tests/unit/test_b.py::test_b\n"
        "tests\\unit\\test_a.py::test_a\n"
        "2/3 tests collected (1 deselected)\n"
    )

    nodes = _selected_nodes(output)

    assert nodes == ["tests/unit/test_a.py::test_a", "tests/unit/test_b.py::test_b"]
    assert _sha256_text(nodes) == _sha256_text(list(reversed(nodes)))


def test_full_command_is_bounded_and_cannot_hide_worker_crashes():
    basetemp = Path("C:/Temp/readme-agent-pytest-xdist")
    command = _pytest_command("python", 4, basetemp)

    assert command[:4] == ["python", "-m", "pytest", "-q"]
    assert command[command.index("-n") + 1] == "4"
    assert command[command.index("--dist") + 1] == "worksteal"
    assert command[command.index("--max-worker-restart") + 1] == "0"
    assert f"--basetemp={basetemp}" in command
