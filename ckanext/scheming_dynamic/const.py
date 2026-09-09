from __future__ import annotations

DEFAULT_ENTITY_TYPE = "dataset"
ENTITY_TYPES = ["dataset", "group", "organization"]

TYPE_FIELDS = {
    "dataset": "dataset_type",
    "group": "group_type",
    "organization": "organization_type",
}

ENTITY_TYPE_URL_PREFIXES = {
    "group": "groups",
    "organization": "organizations",
}
