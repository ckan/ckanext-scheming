from __future__ import annotations

from ckan import types


def scheming_schema_create(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can create dynamic dataset schemas."""
    return {"success": False}


def scheming_schema_update(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can update dynamic dataset schemas."""
    return {"success": False}


def scheming_schema_delete(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can delete dynamic dataset schemas."""
    return {"success": False}


def scheming_preset_create(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can create field presets."""
    return {"success": False}


def scheming_preset_update(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can update field presets."""
    return {"success": False}


def scheming_preset_delete(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can delete field presets."""
    return {"success": False}


def scheming_schema_activity_list(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can view dynamic schema history."""
    return {"success": False}


def scheming_migration_mapping_show(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can view schema migration mappings."""
    return {"success": False}


def scheming_migration_mapping_update(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can author schema migration mappings."""
    return {"success": False}


def scheming_migration_mapping_delete(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can delete schema migration mappings."""
    return {"success": False}


def scheming_migration_status(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can see how far datasets are behind the live schema."""
    return {"success": False}


def scheming_migration_apply(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can migrate datasets between schema versions."""
    return {"success": False}


def scheming_migration_run_list(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can list migration runs."""
    return {"success": False}


def scheming_migration_run_show(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can inspect a migration run."""
    return {"success": False}


def scheming_migration_run_cancel(
    context: types.Context, data_dict: types.DataDict
) -> types.AuthResult:
    """Only sysadmins can cancel a migration run."""
    return {"success": False}


def get_auth_functions():
    return {
        "scheming_schema_create": scheming_schema_create,
        "scheming_schema_update": scheming_schema_update,
        "scheming_schema_delete": scheming_schema_delete,
        "scheming_schema_activity_list": scheming_schema_activity_list,
        "scheming_preset_create": scheming_preset_create,
        "scheming_preset_update": scheming_preset_update,
        "scheming_preset_delete": scheming_preset_delete,
        "scheming_migration_mapping_show": scheming_migration_mapping_show,
        "scheming_migration_mapping_update": scheming_migration_mapping_update,
        "scheming_migration_mapping_delete": scheming_migration_mapping_delete,
        "scheming_migration_status": scheming_migration_status,
        "scheming_migration_apply": scheming_migration_apply,
        "scheming_migration_run_list": scheming_migration_run_list,
        "scheming_migration_run_show": scheming_migration_run_show,
        "scheming_migration_run_cancel": scheming_migration_run_cancel,
    }
