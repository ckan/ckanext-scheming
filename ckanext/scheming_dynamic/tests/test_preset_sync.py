from __future__ import annotations

from typing import Any

import pytest
from freezegun import freeze_time

import ckan.plugins.toolkit as tk

from ckanext.scheming.plugins import _SchemingMixin
from ckanext.scheming_dynamic import sync
from ckanext.scheming_dynamic.tests import factories


@pytest.mark.ckan_config("ckan.plugins", "scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db", "reload_scheming_presets")
class TestPresetSync:
    def _get_presets(self) -> dict[str, dict[str, Any]]:
        return _SchemingMixin.get_presets(tk.config)  # type: ignore

    def test_get_static_presets_includes_builtin_presets(self):
        assert "title" in sync.get_static_presets()

    def test_db_preset_is_merged_into_scheming_presets(self):
        assert "test-preset" not in (self._get_presets() or {})

        factories.Preset(preset_name="test-preset", values={"validators": "not_empty"})
        sync.ensure_presets_synced()

        presets = self._get_presets()

        assert presets
        assert presets["test-preset"] == {"validators": "not_empty"}

    def test_db_preset_does_not_leak_into_static_presets(self):
        factories.Preset(preset_name="test-preset", values={"validators": "not_empty"})
        sync.ensure_presets_synced()

        assert "test-preset" not in sync.get_static_presets()

    def test_update_is_visible_without_restart(self):
        preset = factories.Preset(
            preset_name="test-preset", values={"validators": "not_empty"}
        )
        sync.ensure_presets_synced()

        presets = self._get_presets()
        assert presets["test-preset"] == {"validators": "not_empty"}

        preset.update_values({"validators": "ignore_missing"})
        sync.ensure_presets_synced()

        assert self._get_presets()["test-preset"] == {"validators": "ignore_missing"}

    def test_delete_removes_preset_from_merged_presets(self):
        preset = factories.Preset(
            preset_name="test-preset", values={"validators": "not_empty"}
        )
        sync.ensure_presets_synced()
        assert "test-preset" in self._get_presets()

        preset.delete()
        sync.ensure_presets_synced()

        assert "test-preset" not in self._get_presets()

    def test_db_preset_overrides_builtin_preset_of_the_same_name(self):
        assert self._get_presets()["title"]["form_snippet"] == ("large_text.html")

        factories.Preset(preset_name="title", values={"validators": "not_empty"})
        sync.ensure_presets_synced()

        merged = self._get_presets()["title"]
        assert merged == {"validators": "not_empty"}
        # the static registry itself is untouched, only the served/merged
        # copy is shadowed
        assert sync.get_static_presets()["title"]["form_snippet"] == "large_text.html"

    def test_preset_basing_on_registered_static_preset_resolves(self):
        factories.Preset(preset_name="test-preset", values={"preset": "title"})
        sync.ensure_presets_synced()

        merged = self._get_presets()["test-preset"]
        assert merged["form_snippet"] == "large_text.html"

    def test_unresolvable_base_preset_is_dropped_but_others_survive(self):
        factories.Preset(preset_name="good-preset", values={"validators": "not_empty"})
        factories.Preset(preset_name="bad-preset", values={"preset": "no-such-base"})
        sync.ensure_presets_synced()

        presets = self._get_presets()
        assert "good-preset" in presets
        assert "bad-preset" not in presets

    def test_cyclic_preset_is_dropped_but_others_survive(self):
        factories.Preset(preset_name="a", values={"preset": "b"})
        factories.Preset(preset_name="b", values={"preset": "a"})
        factories.Preset(preset_name="good-preset", values={"validators": "not_empty"})
        sync.ensure_presets_synced()

        presets = self._get_presets()
        assert "good-preset" in presets
        assert "a" not in presets
        assert "b" not in presets

    def test_delete_then_create_at_the_same_instant_is_still_detected(self):
        with freeze_time("2024-01-01T00:00:00Z"):
            factories.Preset(preset_name="anchor", values={"validators": "x"})
            a = factories.Preset(preset_name="a", values={"validators": "x"})

        sync.ensure_presets_synced()
        presets = self._get_presets()
        assert "a" in presets

        with freeze_time("2024-01-01T00:00:00Z"):
            a.delete()
            factories.Preset(preset_name="b", values={"validators": "x"})

        sync.ensure_presets_synced()

        presets = self._get_presets()
        assert "b" in presets
        assert "a" not in presets
