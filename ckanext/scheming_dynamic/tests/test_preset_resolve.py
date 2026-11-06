from __future__ import annotations

import pytest

from ckanext.scheming_dynamic.preset_resolve import (
    PresetBaseNotFoundError,
    PresetCycleError,
    resolve_preset_values,
)


class TestResolvePresetValues:
    def test_preset_without_base_returns_its_own_values(self):
        raw = {"a": {"form_snippet": "text.html"}}

        assert resolve_preset_values("a", raw, {}) == {"form_snippet": "text.html"}

    def test_base_in_static_presets_is_merged_in(self):
        raw = {"a": {"preset": "title"}}
        static = {"title": {"form_snippet": "large_text.html", "validators": "x"}}

        result = resolve_preset_values("a", raw, static)

        assert result == {
            "preset": "title",
            "form_snippet": "large_text.html",
            "validators": "x",
        }

    def test_own_keys_win_over_base_keys(self):
        raw = {"a": {"preset": "title", "form_snippet": "markdown.html"}}
        static = {"title": {"form_snippet": "large_text.html"}}

        result = resolve_preset_values("a", raw, static)

        assert result["form_snippet"] == "markdown.html"

    def test_base_in_raw_db_presets_is_resolved_transitively(self):
        raw = {
            "a": {"preset": "b"},
            "b": {"preset": "c"},
            "c": {"validators": "not_empty"},
        }

        assert resolve_preset_values("a", raw, {}) == {
            "preset": "b",
            "validators": "not_empty",
        }

    def test_own_keys_win_over_transitive_base_keys(self):
        raw = {
            "a": {"preset": "b", "validators": "override"},
            "b": {"preset": "c", "validators": "middle"},
            "c": {"validators": "not_empty"},
        }

        assert resolve_preset_values("a", raw, {})["validators"] == "override"

    def test_self_reference_raises_cycle_error(self):
        raw = {"a": {"preset": "a"}}

        with pytest.raises(PresetCycleError) as err:
            resolve_preset_values("a", raw, {})

        # detected one level down, so the closing name is repeated
        assert err.value.chain == ["a", "a"]

    def test_longer_cycle_raises_cycle_error(self):
        raw = {"a": {"preset": "b"}, "b": {"preset": "a"}}

        with pytest.raises(PresetCycleError) as err:
            resolve_preset_values("a", raw, {})

        assert err.value.chain == ["a", "b", "a"]

    def test_missing_base_raises_base_not_found_error(self):
        raw = {"a": {"preset": "no-such-preset"}}

        with pytest.raises(PresetBaseNotFoundError) as err:
            resolve_preset_values("a", raw, {})

        assert err.value.preset_name == "a"
        assert err.value.base == "no-such-preset"

    def test_static_base_is_preferred_when_name_only_in_static(self):
        raw = {"a": {"preset": "title"}}
        static = {"title": {"form_snippet": "large_text.html"}}

        assert resolve_preset_values("a", raw, static)["form_snippet"] == (
            "large_text.html"
        )
