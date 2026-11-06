from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

import ckan.plugins.toolkit as tk

from ckanext.scheming_dynamic.schema import BaseSchema


def load_data(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")

    if path.suffix in (".yaml", ".yml"):
        return yaml.safe_load(text)

    return json.loads(text)


def iter_errors(data: Any, schema: BaseSchema) -> Iterator[ValidationError]:
    built = schema.build()
    Draft202012Validator.check_schema(built)
    validator = Draft202012Validator(built, format_checker=FormatChecker())
    yield from sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))


def error_location(error: ValidationError) -> str:
    return "/".join(str(p) for p in error.absolute_path) or tk._("<root>")
