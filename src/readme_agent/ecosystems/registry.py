"""Dispatch by ecosystem string. Additive: new ecosystems are new entries, not new call sites."""

from readme_agent.ecosystems import maven
from readme_agent.errors import ConfigError
from readme_agent.inspection.file_inventory import FileInventory

_PARSERS = {
    "maven": lambda inventory: maven.parse_pom(inventory.pom_path) if inventory.pom_path else {},
}


def parse_manifest(ecosystem: str, inventory: FileInventory) -> dict[str, str]:
    parser = _PARSERS.get(ecosystem)
    if parser is None:
        raise ConfigError(
            f"no manifest parser registered for ecosystem {ecosystem!r} (known: {sorted(_PARSERS)})"
        )
    return parser(inventory)
