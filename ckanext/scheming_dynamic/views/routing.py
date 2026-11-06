"""URL-routing helpers shared by the admin and migration blueprints."""

from __future__ import annotations

from typing import Any

from flask import Blueprint

from ckanext.scheming_dynamic.const import DEFAULT_ENTITY_TYPE, ENTITY_TYPE_URL_PREFIXES


def entity_route(
    bp: Blueprint,
    bare_path: str,
    entity_path: str,
    *,
    endpoint: str,
    view_func: Any,
    **kwargs: Any,
) -> None:
    """Register one view under the bare (dataset) path and, per non-dataset
    entity type, under its pluralized-prefix path (``entity_path`` with a
    ``{prefix}`` placeholder) -- sharing a single endpoint so ``url_for``
    picks the right rule from the ``entity_type`` kwarg. The prefix is kept
    distinct from any schema_type value so the common single-type setup
    (schema_type "group" under entity_type "group") doesn't produce a
    doubled URL segment like /group/group/edit.
    """
    bp.add_url_rule(
        bare_path,
        endpoint=endpoint,
        view_func=view_func,
        defaults={"entity_type": DEFAULT_ENTITY_TYPE},
        **kwargs,
    )
    for entity_type, prefix in ENTITY_TYPE_URL_PREFIXES.items():
        bp.add_url_rule(
            entity_path.format(prefix=prefix),
            endpoint=endpoint,
            view_func=view_func,
            defaults={"entity_type": entity_type},
            **kwargs,
        )
