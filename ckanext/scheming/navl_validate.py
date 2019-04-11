# encoding: utf-8

import copy
import formencode as fe
import inspect
import json

from six import text_type
from ckan.common import config
from ckan.lib.navl.dictization_functions import (
    DictizationError,
    StopOnError,
    Invalid,
    DataError,
    Missing,
    State,
    missing,
    flattened_order_key,
    flatten_schema,
    get_all_key_combinations,
    augment_data,
    convert,
    _remove_blank_keys,
    flatten_list,
    flatten_dict,
    unflatten,
    MissingNullEncoder
    
)

from ckan.common import _

def make_full_schema(data, schema):
    '''make schema by getting all valid combinations and making sure that all
    keys are available'''
    flattened_schema = flatten_schema(schema)
    key_combinations = get_all_key_combinations(data, flattened_schema)
    full_schema = {}

    for combination in key_combinations:
        sub_schema = schema
        for key in combination[::2]:
            sub_schema = sub_schema[key]
        if key == "resources" and "resource_schemas" in schema:
            resource_type = data.get(combination + ("resource_type", ))
            if resource_type:
                sub_schema = schema["resource_schemas"][resource_type]

        
        for key, value in sub_schema.iteritems():
            if isinstance(value, list):
                full_schema[combination + (key,)] = value

    return full_schema

def validate(data, schema, context=None):
    '''Validate an unflattened nested dict against a schema.'''
    context = context or {}
    assert isinstance(data, dict)

    # store any empty lists in the data as they will get stripped out by
    # the _validate function. We do this so we can differentiate between
    # empty fields and missing fields when doing partial updates.
    empty_lists = [key for key, value in data.items() if value == []]

    # create a copy of the context which also includes the schema keys so
    # they can be used by the validators
    validators_context = dict(context, schema_keys=schema.keys())

    flattened = flatten_dict(data)
    converted_data, errors = _validate(flattened, schema, validators_context)
    converted_data = unflatten(converted_data)

    # check config for partial update fix option
    if config.get('ckan.fix_partial_updates', True):
        # repopulate the empty lists
        for key in empty_lists:
            if key not in converted_data:
                converted_data[key] = []

    errors_unflattened = unflatten(errors)

    # remove validators that passed
    dicts_to_process = [errors_unflattened]
    while dicts_to_process:
        dict_to_process = dicts_to_process.pop()
        for key, value in dict_to_process.items():
            if not value:
                dict_to_process.pop(key)
                continue
            if isinstance(value[0], dict):
                dicts_to_process.extend(value)

    _remove_blank_keys(errors_unflattened)

    return converted_data, errors_unflattened


def _validate(data, schema, context):
    '''validate a flattened dict against a schema'''
    converted_data = augment_data(data, schema)
    full_schema = make_full_schema(data, schema)

    errors = dict((key, []) for key in full_schema)

    # before run
    for key in sorted(full_schema, key=flattened_order_key):
        if key[-1] == '__before':
            for converter in full_schema[key]:
                try:
                    convert(converter, key, converted_data, errors, context)
                except StopOnError:
                    break

    # main run
    for key in sorted(full_schema, key=flattened_order_key):
        if not key[-1].startswith('__'):
            for converter in full_schema[key]:
                try:
                    convert(converter, key, converted_data, errors, context)
                except StopOnError:
                    break

    # extras run
    for key in sorted(full_schema, key=flattened_order_key):
        if key[-1] == '__extras':
            for converter in full_schema[key]:
                try:
                    convert(converter, key, converted_data, errors, context)
                except StopOnError:
                    break

    # after run
    for key in reversed(sorted(full_schema, key=flattened_order_key)):
        if key[-1] == '__after':
            for converter in full_schema[key]:
                try:
                    convert(converter, key, converted_data, errors, context)
                except StopOnError:
                    break

    # junk
    if ('__junk',) in full_schema:
        for converter in full_schema[('__junk',)]:
            try:
                convert(converter, ('__junk',), converted_data, errors,
                        context)
            except StopOnError:
                break

    return converted_data, errors
