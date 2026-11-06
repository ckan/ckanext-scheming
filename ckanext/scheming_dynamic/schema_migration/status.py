"""How far the entities of each schema type lag behind its live version."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa

from ckan import model

from ckanext.scheming_dynamic.const import DEFAULT_ENTITY_TYPE
from ckanext.scheming_dynamic.model import SchemingSchemaPin, SchemingSchemaVersion


def _entity_model(entity_type: str) -> Any:
    return model.Package if entity_type == DEFAULT_ENTITY_TYPE else model.Group


def for_schema_type(
    entity_type: str, schema_type: str, head_version: int
) -> dict[str, Any]:
    distribution = _distribution(entity_type, schema_type)

    return {
        "entity_type": entity_type,
        "schema_type": schema_type,
        "live_version": head_version,
        "distribution": distribution,
        "behind": sum(
            count for version, count in distribution.items() if version != head_version
        ),
        "unpinned": _unpinned_count(entity_type, schema_type),
    }


def all_schema_types(entity_type: str) -> list[dict[str, Any]]:
    return [
        for_schema_type(entity_type, row.schema_type, row.version)
        for row in SchemingSchemaVersion.get_heads_of_type(entity_type)
    ]


def _distribution(entity_type: str, schema_type: str) -> dict[int, int]:
    entity = _entity_model(entity_type)
    filters = [
        SchemingSchemaPin.entity_type == entity_type,
        SchemingSchemaPin.schema_type == schema_type,
        entity.state == model.State.ACTIVE,
    ]
    if entity_type != DEFAULT_ENTITY_TYPE:
        filters.append(model.Group.is_organization == (entity_type == "organization"))

    rows = (
        model.Session.query(
            SchemingSchemaPin.version, sa.func.count(SchemingSchemaPin.entity_id)
        )
        .join(entity, entity.id == SchemingSchemaPin.entity_id)
        .filter(*filters)
        .group_by(SchemingSchemaPin.version)
        .all()
    )
    return {version: count for version, count in rows}  # noqa C416


def _unpinned_count(entity_type: str, schema_type: str) -> int:
    entity = _entity_model(entity_type)
    filters = [
        entity.type == schema_type,
        entity.state == model.State.ACTIVE,
        ~model.Session.query(SchemingSchemaPin)
        .filter(SchemingSchemaPin.entity_id == entity.id)
        .exists(),
    ]
    if entity_type != DEFAULT_ENTITY_TYPE:
        filters.append(model.Group.is_organization == (entity_type == "organization"))

    return model.Session.query(entity.id).filter(*filters).count()
