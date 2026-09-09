import pytest

from ckanext.scheming.plugins import _SchemingMixin
from ckanext.scheming_dynamic import sync
from ckanext.scheming_dynamic.model import SchemingPreset, SchemingSchemaVersion
from ckanext.scheming_dynamic.tests import factories
from ckanext.scheming_dynamic.tests.helpers import PRESET_DEFINITION, SCHEMA_DEFINITION


@pytest.fixture
def clean_db(reset_db, migrate_db_for):
    reset_db()
    migrate_db_for("scheming_dynamic")


@pytest.fixture(autouse=True)
def reset_schema_sync():
    sync.reset()


@pytest.fixture
def schema_definition() -> dict:
    return {**SCHEMA_DEFINITION}


@pytest.fixture
def preset_definition() -> dict:
    return {**PRESET_DEFINITION}


@pytest.fixture
def reload_scheming_presets():
    """Force _SchemingMixin to reload presets from the current config."""
    _SchemingMixin._presets = None
    yield
    _SchemingMixin._presets = None


@pytest.fixture
def dataset_schema(schema_definition: dict) -> SchemingSchemaVersion:
    return SchemingSchemaVersion.create(
        "dataset", schema_definition["dataset_type"], schema_definition
    )


@pytest.fixture
def preset(preset_definition: dict) -> SchemingPreset:
    return factories.Preset(
        preset_name=preset_definition["preset_name"],
        values=preset_definition["values"],
    )
