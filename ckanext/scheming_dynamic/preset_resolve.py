from __future__ import annotations

from typing import Any


class PresetCycleError(Exception):
    """A preset's ``preset`` (base) chain loops back on itself."""

    def __init__(self, chain: list[str]) -> None:
        self.chain = chain
        super().__init__(" -> ".join([*chain, chain[0]]))


class PresetBaseNotFoundError(Exception):
    """A preset bases on a name that isn't a registered or DB preset."""

    def __init__(self, preset_name: str, base: str) -> None:
        self.preset_name = preset_name
        self.base = base
        super().__init__(f"preset '{preset_name}' bases on unknown preset '{base}'")


def resolve_preset_values(
    name: str,
    raw: dict[str, dict[str, Any]],
    static: dict[str, dict[str, Any]],
    _path: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Flatten a preset's ``values``, merging in its base preset if any.

    ``raw`` holds not-yet-flattened DB preset values (``preset_name`` ->
    ``values``, as stored); ``static`` holds already-flat presets registered
    via ``scheming.presets``. A preset's own keys always win over its
    base's, mirroring ckanext-scheming's own field/preset merge in
    ``ckanext.scheming.plugins._expand``.

    Raises ``PresetCycleError`` if ``name``'s base chain revisits a preset,
    ``PresetBaseNotFoundError`` if a base isn't in ``raw`` or ``static``.
    """
    if name in _path:
        cycle = [*_path[_path.index(name) :], name]
        raise PresetCycleError(cycle)

    values = raw[name]
    base = values.get("preset")
    if not base:
        return dict(values)

    path = (*_path, name)
    if base in raw:
        base_values = resolve_preset_values(base, raw, static, path)
    elif base in static:
        base_values = static[base]
    else:
        raise PresetBaseNotFoundError(name, base)

    return {**base_values, **values}
