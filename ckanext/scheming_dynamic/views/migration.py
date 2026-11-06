from __future__ import annotations

from typing import Any

from flask import Blueprint
from flask.views import MethodView

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.views.admin import before_request

from ckanext.scheming_dynamic.const import DEFAULT_ENTITY_TYPE, ENTITY_TYPES
from ckanext.scheming_dynamic.schema_migration import mapping as mapping_lib
from ckanext.scheming_dynamic.schema_migration.apply import expanded_definition
from ckanext.scheming_dynamic.schema_migration.diff import CONSTANT, COPY
from ckanext.scheming_dynamic.views.routing import entity_route

MIGRATION_BP = "scheming_dynamic_migration"
RUNS_PAGE_SIZE = 20

bp = Blueprint(MIGRATION_BP, __name__, url_prefix="/ckan-admin/scheming/migrations")


def _route_args(entity_type: str) -> dict[str, str]:
    return {} if entity_type == DEFAULT_ENTITY_TYPE else {"entity_type": entity_type}


def _plan_groups(plan: dict[str, Any]) -> list[str]:
    """The field groups this schema actually has (from its diff)."""
    return list(plan["diff"])


def _primary_group(plan: dict[str, Any]) -> str:
    return "dataset_fields" if plan["entity_type"] == DEFAULT_ENTITY_TYPE else "fields"


def index() -> str:
    """Migration status for every schema type, across all entity types."""
    rows = [
        row
        for entity_type in ENTITY_TYPES
        for row in tk.get_action("scheming_migration_status")(
            {}, {"entity_type": entity_type}
        )
    ]
    rows.sort(key=lambda r: (r["entity_type"], r["schema_type"]))

    return tk.render(
        "scheming_dynamic/migration/index.html",
        {
            "rows": rows,
            "active_tab": "migrations",
        },
    )


class MappingView(MethodView):
    def get(
        self,
        schema_type: str,
        from_version: int,
        to_version: int,
        entity_type: str = DEFAULT_ENTITY_TYPE,
        errors: list[str] | None = None,
    ) -> str:
        try:
            plan = _mapping_show(entity_type, schema_type, from_version, to_version)
        except tk.ValidationError as e:
            return tk.abort(404, "; ".join(e.error_summary.values()))

        return tk.render(
            "scheming_dynamic/migration/mapping.html",
            {
                "plan": plan,
                "sources": _source_names(plan),
                "errors": errors or [],
                "entity_type": entity_type,
                "active_tab": "migrations",
            },
        )

    def post(
        self,
        schema_type: str,
        from_version: int,
        to_version: int,
        entity_type: str = DEFAULT_ENTITY_TYPE,
    ) -> Any:
        plan = _mapping_show(entity_type, schema_type, from_version, to_version)

        try:
            tk.get_action("scheming_migration_mapping_update")(
                {},
                {
                    "entity_type": entity_type,
                    "schema_type": schema_type,
                    "from_version": from_version,
                    "to_version": to_version,
                    "mapping": _mapping_from_form(plan, tk.request.form),
                },
            )
        except tk.ValidationError as e:
            return self.get(
                schema_type,
                from_version,
                to_version,
                entity_type,
                list(e.error_summary.values()),
            )

        tk.h.flash_success(tk._("Mapping saved."))

        return tk.redirect_to(
            f"{MIGRATION_BP}.mapping",
            schema_type=schema_type,
            from_version=from_version,
            to_version=to_version,
            **_route_args(entity_type),
        )


def apply_all(
    schema_type: str,
    from_version: int,
    to_version: int,
    entity_type: str = DEFAULT_ENTITY_TYPE,
) -> Any:
    try:
        run = tk.get_action("scheming_migration_apply")(
            {},
            {
                "entity_type": entity_type,
                "schema_type": schema_type,
                "from_version": from_version,
                "to_version": to_version,
                "dry_run": tk.request.form.get("dry_run") == "1",
            },
        )
    except tk.ValidationError as e:
        tk.h.flash_error("; ".join(e.error_summary.values()))
        return tk.redirect_to(
            f"{MIGRATION_BP}.mapping",
            schema_type=schema_type,
            from_version=from_version,
            to_version=to_version,
            **_route_args(entity_type),
        )

    return tk.redirect_to(f"{MIGRATION_BP}.run", run_id=run["id"])


class DatasetView(MethodView):
    """Guided migration of a single entity, asking only the open questions."""

    def get(  # noqa: PLR0913 PLR0917
        self,
        schema_type: str,
        from_version: int,
        to_version: int,
        pkg_id: str,
        entity_type: str = DEFAULT_ENTITY_TYPE,
        errors: dict[str, Any] | None = None,
    ) -> str:
        plan = _mapping_show(entity_type, schema_type, from_version, to_version)
        show_action = _show_action(entity_type)

        return tk.render(
            "scheming_dynamic/migration/dataset.html",
            {
                "plan": plan,
                "dataset": tk.get_action(show_action)({}, {"id": pkg_id}),
                "questions": _open_questions(plan),
                "errors": errors or {},
                "entity_type": entity_type,
                "licenses": model.Package.get_license_options(),
                "active_tab": "migrations",
            },
        )

    def post(  # noqa: PLR0913
        self,
        schema_type: str,
        from_version: int,
        to_version: int,
        pkg_id: str,
        entity_type: str = DEFAULT_ENTITY_TYPE,
    ) -> Any:
        plan = _mapping_show(entity_type, schema_type, from_version, to_version)
        questions = _open_questions(plan)
        group = _primary_group(plan)

        values = {
            group: {
                field["field_name"]: tk.request.form.get(field["field_name"], "")
                for field in questions
            }
        }

        try:
            run = tk.get_action("scheming_migration_apply")(
                {},
                {
                    "entity_type": entity_type,
                    "schema_type": schema_type,
                    "from_version": from_version,
                    "to_version": to_version,
                    "id": pkg_id,
                    "values": values,
                },
            )
        except tk.ValidationError as e:
            return self.get(
                schema_type, from_version, to_version, pkg_id, entity_type, e.error_dict
            )

        item = tk.get_action("scheming_migration_run_show")({}, {"id": run["id"]})[
            "items"
        ][0]

        if item["status"] != "ok":
            return self.get(
                schema_type,
                from_version,
                to_version,
                pkg_id,
                entity_type,
                item["errors"],
            )

        tk.h.flash_success(tk._("Migrated to version {}.").format(to_version))
        return tk.redirect_to(f"{MIGRATION_BP}.run", run_id=run["id"])


def _show_action(entity_type: str) -> str:
    return (
        "package_show" if entity_type == DEFAULT_ENTITY_TYPE else f"{entity_type}_show"
    )


def _open_questions(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """The target fields this entity still has to answer, with their schema."""
    group = _primary_group(plan)
    deferred = {
        problem["field_name"]
        for problem in mapping_lib.manual_fields(plan["mapping"]) + plan["unresolved"]
        if problem["group"] == group
    }

    target = expanded_definition(
        plan["entity_type"], plan["schema_type"], plan["to_version"]
    )
    by_name = {f["field_name"]: f for f in target.get(group, [])}

    return [by_name[name] for name in sorted(deferred) if name in by_name]


def runs() -> str:
    """Recent migration runs for every entity type, newest first."""
    all_runs = [
        run
        for entity_type in ENTITY_TYPES
        for run in tk.get_action("scheming_migration_run_list")(
            {}, {"entity_type": entity_type, "limit": RUNS_PAGE_SIZE}
        )
    ]
    all_runs.sort(key=lambda r: r["started"], reverse=True)

    return tk.render(
        "scheming_dynamic/migration/runs.html",
        {
            "runs": all_runs[:RUNS_PAGE_SIZE],
            "active_tab": "migrations",
        },
    )


def run(run_id: str) -> str:
    try:
        data = tk.get_action("scheming_migration_run_show")({}, {"id": run_id})
    except tk.ObjectNotFound:
        return tk.abort(404, tk._("Migration run not found"))

    return tk.render(
        "scheming_dynamic/migration/run.html",
        {"run": data, "active_tab": "migrations"},
    )


def cancel(run_id: str) -> Any:
    try:
        tk.get_action("scheming_migration_run_cancel")({}, {"id": run_id})
    except tk.ValidationError as e:
        tk.h.flash_error("; ".join(e.error_summary.values()))
    else:
        tk.h.flash_success(tk._("Migration cancelled."))

    return tk.redirect_to(f"{MIGRATION_BP}.run", run_id=run_id)


def _mapping_show(
    entity_type: str, schema_type: str, from_version: int, to_version: int
) -> dict[str, Any]:
    return tk.get_action("scheming_migration_mapping_show")(
        {},
        {
            "entity_type": entity_type,
            "schema_type": schema_type,
            "from_version": from_version,
            "to_version": to_version,
        },
    )


def _source_names(plan: dict[str, Any]) -> dict[str, list[str]]:
    """Field names available as a copy source, per group."""
    names = {}

    for group in _plan_groups(plan):
        group_diff = plan["diff"][group]
        carried = {
            change["source"] for change in group_diff["fields"] if change["source"]
        }
        names[group] = sorted(carried | set(group_diff["dropped"]))

    return names


def _mapping_from_form(plan: dict[str, Any], form: Any) -> dict[str, Any]:
    """Overlay the admin's decisions onto the auto-derived suggestion."""
    groups = _plan_groups(plan)
    mapping = {group: dict(plan["suggested"].get(group, {})) for group in groups}
    mapping["dropped"] = {group: form.getlist(f"dropped.{group}") for group in groups}

    for group in groups:
        for change in plan["diff"][group]["fields"]:
            entry = _entry_from_form(group, change, form)
            if entry:
                mapping[group][change["field_name"]] = entry

    return mapping


def _entry_from_form(
    group: str, change: dict[str, Any], form: Any
) -> dict[str, Any] | None:
    field_name = change["field_name"]
    prefix = f"field.{group}.{field_name}"

    action = form.get(f"{prefix}.action")
    if not action:
        return None

    entry: dict[str, Any] = {"action": action}

    if action == COPY:
        entry["source"] = form.get(f"{prefix}.source") or field_name
        value_map = {
            value: form.get(f"{prefix}.value_map.{value}")
            for value in change["lost_choices"]
            if form.get(f"{prefix}.value_map.{value}")
        }
        if value_map:
            entry["value_map"] = value_map

    if action == CONSTANT:
        entry["value"] = form.get(f"{prefix}.value", "")

    return entry


bp.before_request(before_request)


bp.add_url_rule("/", endpoint="index", view_func=index)
bp.add_url_rule("/runs", endpoint="runs", view_func=runs)
bp.add_url_rule("/runs/<run_id>", view_func=run)
bp.add_url_rule("/runs/<run_id>/cancel", view_func=cancel, methods=["POST"])
entity_route(
    bp,
    "/<schema_type>/<int:from_version>/<int:to_version>",
    "/{prefix}/<schema_type>/<int:from_version>/<int:to_version>",
    endpoint="mapping",
    view_func=MappingView.as_view("mapping"),
)
entity_route(
    bp,
    "/<schema_type>/<int:from_version>/<int:to_version>/apply",
    "/{prefix}/<schema_type>/<int:from_version>/<int:to_version>/apply",
    endpoint="apply_all",
    view_func=apply_all,
    methods=["POST"],
)
entity_route(
    bp,
    "/<schema_type>/<int:from_version>/<int:to_version>/dataset/<pkg_id>",
    "/{prefix}/<schema_type>/<int:from_version>/<int:to_version>/dataset/<pkg_id>",
    endpoint="dataset",
    view_func=DatasetView.as_view("dataset"),
)
