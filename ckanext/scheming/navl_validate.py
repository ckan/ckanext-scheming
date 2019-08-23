# encoding: utf-8

from ckan.common import config
from ckan.lib.navl.dictization_functions import (
    StopOnError,
    flattened_order_key,
    flatten_schema,
    get_all_key_combinations,
    convert,
    _remove_blank_keys,
    flatten_dict,
    unflatten,
    DataError,
    missing
)
import copy


def augment_data(data, schema):
    '''Takes 'flattened' data, compares it with the schema, and returns it with
    any problems marked, as follows:

    * keys in the data not in the schema are moved into a list under new key
      ('__junk')
    * keys in the schema but not data are added as keys with value 'missing'

    DEV NOTE [jonathan@fjelltopp.org] : This is a bit of a hack...
    gunnar@fjelltopp.org added "make_full_schema" below which is an alteration
    of ckan.lib.dictization_functions.make_full_schema. I'm not clear on why he
    did this or what was wrong in the first place.  But the function
    _validate() below calls ckan.lib.dictization_functions.augment_data  which
    in turn calls ckan.lib.dictization_functions.make_full_schema (i.e. NOT
    Gunnar's altered version but the original version).  So I have copied the
    original augment_data function here  so that it imports the correct version
    of make_full_schema.  This seems to fix immediate problems  with
    validation.
    '''
    flattened_schema = flatten_schema(schema)
    key_combinations = get_all_key_combinations(data, flattened_schema)
    full_schema = make_full_schema(data, schema)
    new_data = copy.copy(data)

    # fill junk and extras

    for key, value in new_data.items():
        if key in full_schema:
            continue

        # check if any thing naughty is placed against subschemas
        initial_tuple = key[::2]
        if initial_tuple in [initial_key[:len(initial_tuple)]
                             for initial_key in flattened_schema]:
            if data[key] != []:
                raise DataError('Only lists of dicts can be placed against '
                                'subschema %s, not %s' %
                                (key, type(data[key])))

        if key[:-1] in key_combinations:
            extras_key = key[:-1] + ('__extras',)
            extras = new_data.get(extras_key, {})
            extras[key[-1]] = value
            new_data[extras_key] = extras
        else:
            junk = new_data.get(("__junk",), {})
            junk[key] = value
            new_data[("__junk",)] = junk
        new_data.pop(key)

    # add missing

    for key, value in full_schema.items():
        if key not in new_data and not key[-1].startswith("__"):
            new_data[key] = missing

    return new_data


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
