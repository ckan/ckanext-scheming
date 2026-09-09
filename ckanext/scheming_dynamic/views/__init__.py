"""Catch-all dataset/group/organization routes for types created at runtime.

CKAN registers one blueprint per dataset/group/organization type at startup,
named after the type (that is also what makes ``url_for("<type>.read")``
work). A type created in the database after startup has no such blueprint,
so:

- catch-all blueprints with a ``/<package_type>`` (datasets/resources) or
  ``/<group_type>`` (groups *and* organizations) prefix serve its pages.
  Static blueprint prefixes always win in werkzeug routing, so these only
  receive types that got no dedicated blueprint at startup. Types without a
  matching database schema get a 404.
- the dataset and group catch-alls' ``/<x>/...`` rules overlap on shared
  paths (``/new``, ``/<id>``, ``/edit/<id>``, ...). The dataset blueprint is
  registered first so werkzeug always matches it for those; its
  before-request hook forwards to the equivalent group view when the type
  turns out to be a runtime group/organization instead
  (``_forward_to_group``). Group-only paths (``/about/<id>``,
  ``/members/<id>``, ...) are matched by the group blueprint directly.
- a Flask ``url_build_error_handler`` rebuilds ``url_for("<type>.read")``
  style calls through the catch-all blueprints.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app
from flask import url_for as flask_url_for
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session as SASession
from werkzeug.routing import BuildError

import ckan.plugins.toolkit as tk
from ckan import model, types
from ckan.views.dataset import dataset, register_dataset_plugin_rules
from ckan.views.group import group, register_group_plugin_rules
from ckan.views.resource import (
    register_dataset_plugin_rules as register_resource_rules,
)
from ckan.views.resource import resource

from ckanext.scheming.plugins import (
    SchemingDatasetsPlugin,
    SchemingGroupsPlugin,
    SchemingOrganizationsPlugin,
)
from ckanext.scheming.views import add_paged_form_rules
from ckanext.scheming_dynamic.const import DEFAULT_ENTITY_TYPE
from ckanext.scheming_dynamic.model import SchemingSchemaVersion

from .admin import bp as admin_bp
from .migration import bp as migration_bp

DATASET_BP = "scheming_dynamic"
RESOURCE_BP = "scheming_dynamic_resource"
GROUP_BP = "scheming_dynamic_group"

DATASET_TO_GROUP_ENDPOINT = {
    "search": "index",
    "scheming_new": "new",
    "scheming_edit": "edit",
}


def get_blueprints() -> list[Blueprint]:
    dataset_bp = Blueprint(
        DATASET_BP, dataset.import_name, url_prefix="/<package_type>"
    )
    add_paged_form_rules(dataset_bp)
    register_dataset_plugin_rules(dataset_bp)
    dataset_bp.before_request(_dynamic_type_or_404)

    resource_bp = Blueprint(
        RESOURCE_BP, resource.import_name, url_prefix="/<package_type>/<id>/resource"
    )
    register_resource_rules(resource_bp)
    resource_bp.before_request(_dynamic_type_or_404)

    # One catch-all blueprint serves both runtime-created group *and*
    # organization types: they share ckan.views.group, told apart by the
    # ``is_organization`` view arg that ``_dynamic_group_type_or_404``
    # injects per request from the schema's entity_type.
    group_bp = Blueprint(GROUP_BP, group.import_name, url_prefix="/<group_type>")
    register_group_plugin_rules(group_bp)
    group_bp.before_request(_dynamic_group_type_or_404)

    return [dataset_bp, resource_bp, group_bp, admin_bp, migration_bp]


def build_dynamic_type_url(
    app: types.CKANApp,
    error: BuildError,
    endpoint: str,
    values: dict[str, Any],
) -> str | None:
    """Rebuild dataset URLs for types that exist only in the database.

    Registered as a Flask url_build_error_handler: returning None re-raises
    the original BuildError.
    """
    name, _, view = endpoint.partition(".")

    if not view or name in app.blueprints:
        return None

    # `name` is ambiguous when a dataset type itself ends in "_resource"
    # (e.g. "water_resource.read" could be the dataset type "water_resource"
    # or the resource blueprint for type "water"): try it as a dataset type
    # first, since that's the type actually registered in the database.
    if _dynamic_schema_exists(DEFAULT_ENTITY_TYPE, name):
        return flask_url_for(f"{DATASET_BP}.{view}", **{**values, "package_type": name})

    if name.endswith("_resource"):
        package_type = name[: -len("_resource")]
        if _dynamic_schema_exists(DEFAULT_ENTITY_TYPE, package_type):
            return flask_url_for(
                f"{RESOURCE_BP}.{view}", **{**values, "package_type": package_type}
            )

    if _dynamic_schema_exists("group", name) or _dynamic_schema_exists(
        "organization", name
    ):
        return flask_url_for(f"{GROUP_BP}.{view}", **{**values, "group_type": name})

    return None


def _dynamic_schema_exists(entity_type: str, schema_type: str) -> bool:
    # An unsaved schema being previewed (admin.py:preview) has no database
    # row yet, so it needs this escape hatch to still resolve its own URLs.
    if schema_type == getattr(tk.g, "scheming_dynamic_preview_type", None):
        return True

    try:
        with SASession(bind=model.meta.engine) as session:
            return (
                SchemingSchemaVersion.head_version(
                    entity_type, schema_type, session=session
                )
                > 0
            )
    except DBAPIError:
        return False


def _dynamic_type_or_404() -> Any:
    view_args = tk.request.view_args or {}
    package_type = view_args.get("package_type")

    if package_type and SchemingSchemaVersion.head_version(
        DEFAULT_ENTITY_TYPE, package_type
    ):
        _sync_scheming_datasets_plugin()
        return None

    # resource paths have no group/organization equivalent
    if package_type and tk.request.blueprint == DATASET_BP:
        forwarded = _forward_to_group(package_type, view_args)
        if forwarded is not None:
            return forwarded

    return tk.abort(404, tk._("Dataset type not found"))


def _forward_to_group(group_type: str, view_args: dict[str, Any]) -> Any:
    """Run the equivalent group view for a runtime group/organization type.

    The dataset catch-all wins werkzeug routing for the paths it shares with
    the group catch-all; when the type is actually a group/organization, hand
    the request to the matching ``ckan.views.group`` view instead of 404ing.
    Returns None when this isn't a group/organization type (or has no
    equivalent view), so the caller falls through to its own 404.
    """
    is_org = SchemingSchemaVersion.head_version("organization", group_type) > 0
    if not is_org and not SchemingSchemaVersion.head_version("group", group_type):
        return None

    short = (tk.request.endpoint or "").rsplit(".", 1)[-1]
    short = DATASET_TO_GROUP_ENDPOINT.get(short, short)
    view_func = current_app.view_functions.get(f"{GROUP_BP}.{short}")
    if view_func is None:
        return None

    _sync_scheming_group_plugins()

    kwargs = {k: v for k, v in view_args.items() if k != "package_type"}
    kwargs["group_type"] = group_type
    kwargs["is_organization"] = is_org

    return current_app.ensure_sync(view_func)(**kwargs)


def _sync_scheming_datasets_plugin() -> None:
    """Force SchemingDatasetsPlugin to claim this request's package_type.

    ``ckan.views.dataset`` resolves the form/template plugin via
    ``lookup_package_plugin(package_type)`` as one of the very first things
    it does (e.g. building the ``package_form`` snippet), which reads a
    dict SchemingDatasetsPlugin only updates as a side effect of its own
    lazy DB sync (``SchemingDatasetsPlugin._schemas``/``_expanded_schemas``).
    Nothing else guarantees that sync has run yet on a freshly created
    type's very first request in a worker -- without this, that request
    still sees the default IDatasetForm/templates.
    """
    plugin = SchemingDatasetsPlugin.instance

    if plugin is not None:
        plugin._sync_dynamic_schemas()


def _dynamic_group_type_or_404() -> None:
    """Serve runtime-created group/organization types via this catch-all.

    Types registered at startup keep their own blueprints, which take
    precedence; anything reaching here without a matching database schema
    gets a 404. ``is_organization`` is injected into the request's view
    args from the schema's entity_type, since the shared group views take
    it as a keyword argument the catch-all blueprint can't supply
    statically.
    """
    view_args = tk.request.view_args or {}
    group_type = view_args.get("group_type")

    if not group_type:
        tk.abort(404, tk._("Group type not found"))

    if SchemingSchemaVersion.head_version("organization", group_type):
        view_args["is_organization"] = True
    elif SchemingSchemaVersion.head_version("group", group_type):
        view_args["is_organization"] = False
    else:
        tk.abort(404, tk._("Group type not found"))

    _sync_scheming_group_plugins()


def _sync_scheming_group_plugins() -> None:
    """Force the group/organization scheming plugins to claim this type.

    Mirrors ``_sync_scheming_datasets_plugin``: ``ckan.views.group``
    resolves the form/template plugin via ``lookup_group_plugin`` from a
    dict the scheming plugins only refresh as a side effect of their lazy
    DB sync.
    """
    for plugin in (
        SchemingGroupsPlugin.instance,
        SchemingOrganizationsPlugin.instance,
    ):
        if plugin is not None:
            plugin._sync_dynamic_schemas()
