from __future__ import annotations

from typing import Any

import ckan.plugins.toolkit as tk

from ckanext.scheming_dynamic import sync
from ckanext.scheming_dynamic.const import DEFAULT_ENTITY_TYPE
from ckanext.scheming_dynamic.model import SchemingSchemaPin


def dynamic_scheming_get_entity_schema(
    schema_type: str,
    entity_type: str = DEFAULT_ENTITY_TYPE,
    entity_id: str | None = None,
) -> dict[str, Any] | None:
    """Return the expanded schema for an entity, honoring its version pin.

    Mirrors ``h.scheming_get_schema``, but when ``entity_id`` names an
    existing, pinned entity, returns the schema locked at pin time instead
    of the live one — so an edit form doesn't render fields from a schema
    edited after the entity was created. With no ``entity_id`` (creation
    flow) or no pin recorded, falls back to the live schema.
    """
    live = tk.h.scheming_get_schema(entity_type, schema_type)
    if live is None or entity_id is None:
        return live

    pinned = sync.pinned_expanded_schema(entity_type, schema_type, entity_id)
    return pinned if pinned is not None else live


def dynamic_scheming_get_entity_pin_version(
    entity_type: str, entity_id: str | None
) -> int | None:
    """Return the schema version an entity is pinned to, or None if unpinned."""
    if not entity_id:
        return None

    pin = SchemingSchemaPin.get(entity_type, entity_id)
    return pin.version if pin is not None else None
