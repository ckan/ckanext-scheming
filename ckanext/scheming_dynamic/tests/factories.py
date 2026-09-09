from __future__ import annotations

from factory.alchemy import SQLAlchemyModelFactory
from factory.declarations import LazyFunction, Sequence

from ckan import model as ckan_model

from ckanext.scheming_dynamic.model import SchemingPreset


class Preset(SQLAlchemyModelFactory):
    """Preset factory.

    Creates a ``SchemingPreset`` directly via the model, bypassing the
    ``scheming_preset_create`` action (and its validation).
    """

    class Meta:  # type: ignore
        model = SchemingPreset
        sqlalchemy_session = ckan_model.Session

    preset_name = Sequence(lambda n: f"test-preset-{n}")
    values = LazyFunction(lambda: {"validators": "not_empty unicode_safe"})

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.create(kwargs["preset_name"], kwargs["values"])
