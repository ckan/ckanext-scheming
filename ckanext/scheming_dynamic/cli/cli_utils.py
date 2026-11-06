"""Pieces shared by the top-level CLI and the per-feature command groups."""

from __future__ import annotations

from typing import Any

import click

import ckan.plugins.toolkit as tk
from ckan import types

from ckanext.scheming_dynamic.const import DEFAULT_ENTITY_TYPE
from ckanext.scheming_dynamic.schema import SCHEMA_CLASSES

entity_type_option = click.option(
    "-t",
    "--type",
    "entity_type",
    type=click.Choice(sorted(SCHEMA_CLASSES)),
    default=DEFAULT_ENTITY_TYPE,
    show_default=True,
    help="Which ckanext-scheming schema shape to build/validate against.",
)


def site_user_context() -> types.Context:
    return types.Context(
        user=tk.get_action("get_site_user")({"ignore_auth": True}, {})["name"],
        ignore_auth=True,
    )


def call_action(ctx: click.Context, action: str, data: dict[str, Any]) -> Any:
    try:
        return tk.get_action(action)(site_user_context(), data)
    except tk.ObjectNotFound as e:
        click.secho(str(e), fg="red")
        ctx.exit(1)
    except tk.ValidationError as e:
        echo_validation_error(e)
        ctx.exit(1)


def echo_validation_error(error: tk.ValidationError) -> None:
    for field, messages in error.error_dict.items():
        for message in messages if isinstance(messages, list) else [messages]:
            click.secho(f"  {field}: {message}", fg="red")
