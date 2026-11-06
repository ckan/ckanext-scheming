from __future__ import annotations

SCHEMA_DEFINITION = {
    "about": "Example schema",
    "dataset_type": "test-type",
    "dataset_fields": [{"field_name": "temporal_coverage"}],
    "resource_fields": [{"field_name": "url"}],
}

PRESET_DEFINITION = {
    "preset_name": "test-preset",
    "values": {"validators": "not_empty unicode_safe"},
}
