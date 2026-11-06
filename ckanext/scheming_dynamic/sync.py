from __future__ import annotations

import logging
from typing import Any

from flask import g, has_request_context
from sqlalchemy.exc import DBAPIError, UnboundExecutionError

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.scheming.plugins import _expand_schemas, _SchemingMixin
from ckanext.scheming_dynamic.const import DEFAULT_ENTITY_TYPE, ENTITY_TYPES
from ckanext.scheming_dynamic.model import (
    SchemingPreset,
    SchemingSchemaPin,
    SchemingSchemaVersion,
    SchemingState,
)
from ckanext.scheming_dynamic.preset_resolve import (
    PresetBaseNotFoundError,
    PresetCycleError,
    resolve_preset_values,
)

log = logging.getLogger(__name__)

_expanded_version_cache: dict[tuple[str, str, int], dict[str, Any]] = {}

SCHEMA_CHECKED_FLAG = "scheming_dynamic_schema_checked"
PRESET_CHECKED_FLAG = "scheming_dynamic_preset_checked"


def _schema_checked_flag(entity_type: str) -> str:
    return f"{SCHEMA_CHECKED_FLAG}_{entity_type}"


def schemas_if_changed(
    entity_type: str,
    static_schemas: dict[str, Any],
) -> dict[str, Any] | None:
    """Return a copy of ``static_schemas`` overlaid with the database schemas.

    When the database changed since the last call, all schemas of
    ``entity_type`` are rebuilt from the file-defined ones overlaid with the
    database rows. The check runs at most once per request and once per
    worker process, which is how changes made in one worker propagate to the
    others.

    The fingerprint is only advanced once the caller confirms the merged
    schemas were applied successfully (see ``confirm_applied``) — otherwise a
    schema that fails to expand would never be retried until some unrelated
    write bumped the fingerprint again.
    """
    if _checked_in_this_request(_schema_checked_flag(entity_type)):
        return None

    # fields can reference DB-defined presets: their expansion below
    # needs _SchemingMixin._presets to be current first.
    ensure_presets_synced()

    state = _SchemingMixin.dynamic_scheming["schema"][entity_type]
    preset_fingerprint = _SchemingMixin.dynamic_scheming["preset"]["fingerprint"]

    try:
        fingerprint = (SchemingState.fingerprint(entity_type), preset_fingerprint)
    except (DBAPIError, UnboundExecutionError):
        model.Session.rollback()
        log.debug("cannot read the scheming_state table")
        return None

    if fingerprint == state["fingerprint"]:
        return None

    try:
        heads = SchemingSchemaVersion.get_heads_of_type(entity_type=entity_type)
    except (DBAPIError, UnboundExecutionError):
        model.Session.rollback()
        log.debug("cannot read the scheming_schema_version table")
        return None

    merged = dict(static_schemas)

    for row in heads:
        merged[row.schema_type] = row.definition

    state["pending_fingerprint"] = fingerprint

    return merged


def confirm_applied(entity_type: str = DEFAULT_ENTITY_TYPE) -> None:
    """Confirm a successful sync of the dynamic schemas.

    Record that the schemas from the last ``schemas_if_changed`` call were
    successfully applied, so that unchanged database state isn't re-merged on
    the next check.

    Must not be called after a failed merge: the fingerprint would advance
    without the failing schema ever being retried.
    """
    state = _SchemingMixin.dynamic_scheming["schema"][entity_type]
    state["fingerprint"] = state["pending_fingerprint"]


def get_static_presets() -> dict[str, dict[str, Any]]:
    """Return the file/config-registered presets, capturing them if needed."""
    ensure_presets_synced()
    return dict(_SchemingMixin.dynamic_scheming["preset"]["static"] or {})


def ensure_presets_synced() -> None:
    """Overlay the database presets onto ``_SchemingMixin._presets``.

    Mirrors ``schemas_if_changed``: runs at most once per request/worker
    check, keyed off the ``scheming_state`` row for the "preset" key. A
    preset whose base chain fails to resolve (cycle or missing base) is
    dropped and logged rather than breaking every other preset.
    """
    if _checked_in_this_request(PRESET_CHECKED_FLAG):
        return

    state = _SchemingMixin.dynamic_scheming["preset"]

    if state["static"] is None:
        state["static"] = dict(_SchemingMixin.get_presets(tk.config) or {})

    try:
        fingerprint = SchemingState.fingerprint(SchemingPreset.PRESET_STATE_ENTITY_TYPE)
    except (DBAPIError, UnboundExecutionError):
        model.Session.rollback()
        log.debug("cannot read the scheming_state table")
        return

    if fingerprint == state["fingerprint"]:
        return

    try:
        raw = {row.preset_name: row.values for row in SchemingPreset.get_all()}
    except (DBAPIError, UnboundExecutionError):
        model.Session.rollback()
        log.debug("cannot read the scheming_preset table")
        return

    merged = dict(state["static"])
    for name in raw:
        try:
            merged[name] = resolve_preset_values(name, raw, state["static"])
        except (PresetCycleError, PresetBaseNotFoundError):
            log.exception("dropping preset '%s': cannot resolve its base chain", name)

    _SchemingMixin._presets = merged
    state["fingerprint"] = fingerprint


def pinned_expanded_schema(
    entity_type: str, schema_type: str, entity_id: str | None
) -> dict[str, Any] | None:
    """Return the expanded schema an entity was pinned to, if it differs from HEAD.

    Returns None when there's no pin (predates this feature, or the schema
    was never locked) or the pin already points at the current HEAD, so the
    caller can fall back to its normal (live) expanded schema.

    ``version_row.expanded`` is a snapshot taken when the version was
    locked, so it can't drift when a preset is edited afterwards -- read it
    straight instead of re-expanding ``definition`` against the *current*
    preset registry. Rows locked before ``expanded`` existed have it as
    ``None``; those still re-expand live, same as before.

    Results are cached by (entity_type, schema_type, version) for the life
    of the process: locked versions -- and now their expansion snapshot --
    are immutable, so there's nothing to invalidate.
    """
    if not entity_id:
        return None

    pin = SchemingSchemaPin.get(entity_type, entity_id)
    if pin is None:
        return None

    if pin.version == SchemingSchemaVersion.head_version(entity_type, schema_type):
        return None

    cache_key = (entity_type, schema_type, pin.version)
    if cache_key not in _expanded_version_cache:
        version_row = SchemingSchemaVersion.get(entity_type, schema_type, pin.version)
        if version_row is None:
            return None
        if version_row.expanded is not None:
            _expanded_version_cache[cache_key] = version_row.expanded
        else:
            _expanded_version_cache[cache_key] = _expand_schemas(
                {schema_type: version_row.definition}
            )[schema_type]

    return _expanded_version_cache[cache_key]


def reset() -> None:
    """Drop every cached fingerprint/snapshot of the dynamic schemas.

    The next read then re-merges the DB rows from scratch. Used for test
    isolation, and by ``SchemingDatasetsPlugin.configure`` after a runtime
    ``plugins_update()`` reloads the file schemas, so the fingerprint can't
    skip the re-merge.
    """
    _SchemingMixin.dynamic_scheming["schema"] = {
        entity_type: {"fingerprint": None, "pending_fingerprint": None}
        for entity_type in ENTITY_TYPES
    }
    _SchemingMixin.dynamic_scheming["preset"] = {"fingerprint": None, "static": None}
    _SchemingMixin._presets = None
    _expanded_version_cache.clear()


def forget_request_check() -> None:
    """Make the next read re-check the database, as a new request would.

    The per-request check means a schema locked after something already read
    the schemas in the same request stays invisible until the next one.
    """
    if not has_request_context():
        return

    for entity_type in ENTITY_TYPES:
        g.pop(_schema_checked_flag(entity_type), None)
    g.pop(PRESET_CHECKED_FLAG, None)


def _checked_in_this_request(flag: str) -> bool:
    if not has_request_context():
        return False

    if g.get(flag):
        return True

    setattr(g, flag, True)
    return False
