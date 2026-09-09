from ckan import types
from ckan.logic.schema import validator_args

from ckanext.scheming_dynamic.const import DEFAULT_ENTITY_TYPE, ENTITY_TYPES


@validator_args
def scheming_schema_create(
    not_missing: types.Validator,
    unicode_safe: types.Validator,
    convert_to_json_if_string: types.Validator,
    scheming_default_entity_type: types.DataValidator,
    scheming_definition_valid: types.DataValidator,
    one_of: types.ValidatorFactory,
    default: types.ValidatorFactory,
) -> types.Schema:
    return {
        "__before": [scheming_default_entity_type],
        "entity_type": [
            default(DEFAULT_ENTITY_TYPE),
            unicode_safe,
            one_of(ENTITY_TYPES),
        ],
        "definition": [
            not_missing,
            convert_to_json_if_string,
            scheming_definition_valid,
        ],
    }


@validator_args
def scheming_schema_update(
    not_missing: types.Validator,
    unicode_safe: types.Validator,
    scheming_schema_exists: types.DataValidator,
) -> types.Schema:
    schema = scheming_schema_create()

    schema["schema_type"] = [not_missing, unicode_safe, scheming_schema_exists]

    return schema


@validator_args
def scheming_schema_delete(
    scheming_schema_not_in_use: types.DataValidator,
    not_missing: types.Validator,
    unicode_safe: types.Validator,
    scheming_schema_exists: types.DataValidator,
    one_of: types.ValidatorFactory,
    default: types.ValidatorFactory,
) -> types.Schema:
    return {
        "schema_type": [
            not_missing,
            unicode_safe,
            scheming_schema_exists,
            scheming_schema_not_in_use,
        ],
        "entity_type": [
            default(DEFAULT_ENTITY_TYPE),
            unicode_safe,
            one_of(ENTITY_TYPES),
        ],
    }


@validator_args
def scheming_schema_activity_list(
    not_missing: types.Validator,
    unicode_safe: types.Validator,
    one_of: types.ValidatorFactory,
    default: types.ValidatorFactory,
) -> types.Schema:
    return {
        "schema_type": [not_missing, unicode_safe],
        "entity_type": [
            default(DEFAULT_ENTITY_TYPE),
            unicode_safe,
            one_of(ENTITY_TYPES),
        ],
    }


@validator_args
def scheming_preset_create(
    not_missing: types.Validator,
    unicode_safe: types.Validator,
    convert_to_json_if_string: types.Validator,
    scheming_preset_values_valid: types.DataValidator,
) -> types.Schema:
    return {
        "preset_name": [not_missing, unicode_safe],
        "values": [
            not_missing,
            convert_to_json_if_string,
            scheming_preset_values_valid,
        ],
    }


@validator_args
def scheming_preset_update(
    not_missing: types.Validator,
    unicode_safe: types.Validator,
    scheming_preset_exists: types.DataValidator,
) -> types.Schema:
    schema = scheming_preset_create()

    schema["preset_name"] = [not_missing, unicode_safe, scheming_preset_exists]

    return schema


@validator_args
def scheming_preset_delete(
    scheming_preset_not_in_use: types.DataValidator,
    not_missing: types.Validator,
    unicode_safe: types.Validator,
    scheming_preset_exists: types.DataValidator,
) -> types.Schema:
    return {
        "preset_name": [
            not_missing,
            unicode_safe,
            scheming_preset_exists,
            scheming_preset_not_in_use,
        ],
    }


@validator_args
def _migration_version_pair(
    not_missing: types.Validator,
    unicode_safe: types.Validator,
    int_validator: types.Validator,
    scheming_schema_exists: types.DataValidator,
    scheming_migration_versions_valid: types.DataValidator,
    one_of: types.ValidatorFactory,
    default: types.ValidatorFactory,
) -> types.Schema:
    return {
        "entity_type": [
            default(DEFAULT_ENTITY_TYPE),
            unicode_safe,
            one_of(ENTITY_TYPES),
        ],
        "schema_type": [not_missing, unicode_safe, scheming_schema_exists],
        "from_version": [not_missing, int_validator],
        "to_version": [not_missing, int_validator, scheming_migration_versions_valid],
    }


@validator_args
def scheming_migration_mapping_show(
    scheming_default_entity_type: types.DataValidator,
) -> types.Schema:
    return {"__before": [scheming_default_entity_type], **_migration_version_pair()}


@validator_args
def scheming_migration_mapping_update(
    not_missing: types.Validator,
    convert_to_json_if_string: types.Validator,
    scheming_migration_mapping_valid: types.DataValidator,
) -> types.Schema:
    schema = scheming_migration_mapping_show()
    schema["mapping"] = [
        not_missing,
        convert_to_json_if_string,
        scheming_migration_mapping_valid,
    ]
    return schema


def scheming_migration_mapping_delete() -> types.Schema:
    return scheming_migration_mapping_show()


@validator_args
def scheming_migration_status(
    ignore_missing: types.Validator,
    unicode_safe: types.Validator,
    one_of: types.ValidatorFactory,
    default: types.ValidatorFactory,
) -> types.Schema:
    return {
        "entity_type": [
            default(DEFAULT_ENTITY_TYPE),
            unicode_safe,
            one_of(ENTITY_TYPES),
        ],
        "schema_type": [ignore_missing, unicode_safe],
    }


@validator_args
def scheming_migration_apply(
    ignore_missing: types.Validator,
    unicode_safe: types.Validator,
    boolean_validator: types.Validator,
    convert_to_json_if_string: types.Validator,
    scheming_default_entity_type: types.DataValidator,
) -> types.Schema:
    schema = scheming_migration_mapping_show()
    schema["__before"] = [scheming_default_entity_type]
    schema["id"] = [ignore_missing, unicode_safe]
    schema["dry_run"] = [ignore_missing, boolean_validator]
    schema["values"] = [ignore_missing, convert_to_json_if_string]
    return schema


@validator_args
def scheming_migration_run_list(
    ignore_missing: types.Validator,
    unicode_safe: types.Validator,
    int_validator: types.Validator,
    one_of: types.ValidatorFactory,
    default: types.ValidatorFactory,
) -> types.Schema:
    return {
        "entity_type": [
            default(DEFAULT_ENTITY_TYPE),
            unicode_safe,
            one_of(ENTITY_TYPES),
        ],
        "schema_type": [ignore_missing, unicode_safe],
        "limit": [default(20), int_validator],
        "offset": [default(0), int_validator],
    }


@validator_args
def scheming_migration_run_show(
    not_missing: types.Validator,
    unicode_safe: types.Validator,
) -> types.Schema:
    return {"id": [not_missing, unicode_safe]}


def scheming_migration_run_cancel() -> types.Schema:
    return scheming_migration_run_show()
