"""Materialize and validate capability input/output contract models."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, StrictBool, StrictInt, StrictStr, create_model

from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.errors import ConfigError

_JSON_TYPES: dict[str, type[Any]] = {
    "array": list[Any],
    "boolean": StrictBool,
    "integer": StrictInt,
    "object": dict[str, Any],
    "string": StrictStr,
}


def _model_name(capability_id: str, suffix: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", capability_id)
    return "".join(word[:1].upper() + word[1:] for word in words) + suffix


def _annotation(type_name: str, *, capability_id: str, field_name: str) -> type[Any]:
    annotation = _JSON_TYPES.get(type_name)
    if annotation is None:
        raise ConfigError(
            f"{capability_id!r} field {field_name!r} declares unsupported contract type "
            f"{type_name!r}"
        )
    return annotation


def _input_model(manifest: CapabilityManifest) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for field_name, type_name in manifest.required_inputs.items():
        fields[field_name] = (
            _annotation(type_name, capability_id=manifest.capability_id, field_name=field_name),
            ...,
        )
    for field_name, type_name in manifest.optional_inputs.items():
        annotation = _annotation(
            type_name,
            capability_id=manifest.capability_id,
            field_name=field_name,
        )
        fields[field_name] = (annotation | None, None)
    return create_model(
        _model_name(manifest.capability_id, "Input"),
        __config__=ConfigDict(extra="forbid"),
        **fields,
    )


def _output_model(manifest: CapabilityManifest) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for field_name, type_name in manifest.produced_outputs.items():
        annotation = _annotation(
            type_name,
            capability_id=manifest.capability_id,
            field_name=field_name,
        )
        fields[field_name] = (annotation | None, None)
    return create_model(
        _model_name(manifest.capability_id, "Output"),
        __config__=ConfigDict(extra="allow"),
        **fields,
    )


def materialize_contract_models(manifest: CapabilityManifest) -> CapabilityManifest:
    """Return a manifest with concrete Pydantic models on both contract boundaries."""

    if not manifest.produced_outputs:
        raise ConfigError(f"{manifest.capability_id!r} declares no produced_outputs contract")
    return manifest.model_copy(
        update={
            "input_model": manifest.input_model or _input_model(manifest),
            "output_model": manifest.output_model or _output_model(manifest),
        }
    )
