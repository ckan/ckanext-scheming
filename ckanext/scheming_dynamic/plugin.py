from collections.abc import Callable
from functools import partial
from typing import Any, cast

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan import model, types
from ckan.common import CKANConfig

from ckanext.scheming_dynamic import views
from ckanext.scheming_dynamic.cli import get_commands
from ckanext.scheming_dynamic.utils import ensure_pinned, remove_pin


@tk.blanket.actions
@tk.blanket.cli(get_commands)
@tk.blanket.auth_functions
@tk.blanket.validators
@tk.blanket.blueprints(views.get_blueprints)
@tk.blanket.helpers
class SchemingDynamicPlugin(p.SingletonPlugin):
    p.implements(p.IMiddleware, inherit=True)
    p.implements(p.IConfigurer)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.IGroupController, inherit=True)
    p.implements(p.IOrganizationController, inherit=True)

    # IConfigurer

    def update_config(self, config: CKANConfig) -> None:
        tk.add_template_directory(config, "templates")
        tk.add_resource("assets", "scheming-dynamic")

    # IMiddleware

    def make_middleware(self, app: types.CKANApp, config: CKANConfig) -> types.CKANApp:
        # url_for("<type>.read") for types created after startup
        if hasattr(app, "url_build_error_handlers"):
            app.url_build_error_handlers.append(
                cast(
                    "Callable[[Exception, str, dict[str, Any]], str]",
                    partial(views.build_dynamic_type_url, app),
                )
            )
        return app

    # IPackageController / IGroupController / IOrganizationController

    def create(self, entity: "model.Package | model.Group") -> None:
        """Pin an entity to the schema's current head version.

        All three interfaces declare a same-named create(entity) hook, so a
        single plugin implementing all of them needs one dispatching method
        rather than three same-named defs (the last one would silently win
        and get called for every entity type).
        """
        ensure_pinned(self._entity_type(entity), entity.id, entity.type)

    def delete(self, entity: "model.Package | model.Group") -> None:
        """Drop the entity's schema pin as it is (soft-)deleted.

        The counterpart to ``create``; dispatches across the three
        controller interfaces the same way. Only ``package_delete`` and the
        group/org deletes reach here -- ``dataset_purge`` and raw-SQL
        deletions (e.g. ``harvest_source_clear``) do not, which is why
        ``SchemingSchemaVersion.delete_all`` still sweeps stale pins.
        """
        remove_pin(self._entity_type(entity), entity.id)

    @staticmethod
    def _entity_type(entity: "model.Package | model.Group") -> str:
        if isinstance(entity, model.Group):
            return "organization" if entity.is_organization else "group"
        return "dataset"
