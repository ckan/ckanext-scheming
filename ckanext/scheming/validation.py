import json
import datetime
import re
import ckan.lib.helpers as h

from ckantoolkit import get_validator, UnknownValidator, missing, Invalid, _

from ckanext.scheming.errors import SchemingException

OneOf = get_validator('OneOf')
ignore_missing = get_validator('ignore_missing')
not_empty = get_validator('not_empty')

def scheming_validator(fn):
    """
    Decorate a validator that needs to have the scheming fields
    passed with this function. When generating navl validator lists
    the function decorated will be called passing the field
    and complete schema to produce the actual validator for each field.
    """
    fn.is_a_scheming_validator = True
    return fn


@scheming_validator
def scheming_choices(field, schema):
    """
    Require that one of the field choices values is passed.
    """
    return OneOf([c['value'] for c in field['choices']])


@scheming_validator
def scheming_required(field, schema):
    """
    not_empty if field['required'] else ignore_missing
    """
    if field.get('required'):
        return not_empty
    return ignore_missing


@scheming_validator
def scheming_multiple_choice(field, schema):
    """
    Accept zero or more values from a list of choices and convert
    to a json list for storage:

    1. a list of strings, eg.:

       ["choice-a", "choice-b"]

    2. a single string for single item selection in form submissions:

       "choice-a"
    """
    choice_values = set(c['value'] for c in field['choices'])

    def validator(key, data, errors, context):
        # if there was an error before calling our validator
        # don't bother with our validation
        if errors[key]:
            return

        value = data[key]
        if value is not missing:
            if isinstance(value, basestring):
                value = [value]
            elif not isinstance(value, list):
                errors[key].append(_('expecting list of strings'))
                return
        else:
            value = []

        selected = set()
        for element in value:
            if element in choice_values:
                selected.add(element)
                continue
            errors[key].append(_('unexpected choice "%s"') % element)

        if not errors[key]:
            if 'vocabulary' not in field:
                data[key] = json.dumps([
                    c['value'] for c in field['choices']
                    if c['value'] in selected])

            if field.get('required') and not selected:
                errors[key].append(_('Select at least one'))

    return validator

@scheming_validator
def scheming_isodatetime(field, schema):
    def validator(key, data, errors, context):
        value = data[key]
        date_error = _('Date format incorrect')
        time_error = _('Time format incorrect')

        date = None

        if isinstance(value, datetime.datetime):
            return value
        if value is not missing:
            try:
                 date = h.date_str_to_datetime(value)
            except (TypeError, ValueError), e:
                raise Invalid(date_error)
        else:
            extras = data.get(('__extras',))
            if not extras or key[0] + '_date' not in extras:
                if field.get('required'):
                    not_empty(key, data, errors, context)
            else:
                def get_input(suffix):
                    inpt = key[0] + '_' + suffix
                    new_key = (inpt,) + tuple(x for x in key if x != key[0])
                    value = extras[inpt]
                    data[new_key] = value
                    errors[new_key] = []

                    del extras[inpt]

                    if field.get('required'):
                        not_empty(new_key, data, errors, context)

                    return (new_key, value)

                date_key, value = get_input('date')
                value_full = ''
                if value != '':
                    try:
                        value_full = value
                        date = h.date_str_to_datetime(value)
                    except (TypeError, ValueError), e:
                        return errors[date_key].append(date_error)

                time_key, value = get_input('time')
                if value != '':
                    if value_full == '':
                        return errors[date_key].append(_('Date is required when a time is provided'))

                    try:
                        value_full += ' ' + value
                        date = h.date_str_to_datetime(value_full)
                    except (TypeError, ValueError), e:
                        return errors[time_key].append(time_error)

        data[key] = date

    return validator

def scheming_multiple_choice_output(value):
    """
    return stored json as a proper list
    """
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return [value]


def validators_from_string(s, field, schema):
    """
    convert a schema validators string to a list of validators

    e.g. "if_empty_same_as(name) unicode" becomes:
    [if_empty_same_as("name"), unicode]
    """
    out = []
    parts = s.split()
    for p in parts:
        if '(' in p and p[-1] == ')':
            name, args = p.split('(', 1)
            args = args[:-1].split(',')  # trim trailing ')', break up
            v = get_validator_or_converter(name)(*args)
        else:
            v = get_validator_or_converter(p)
        if getattr(v, 'is_a_scheming_validator', False):
            v = v(field, schema)
        out.append(v)
    return out


def get_validator_or_converter(name):
    """
    Get a validator or converter by name
    """
    if name == 'unicode':
        return unicode
    try:
        v = get_validator(name)
        return v
    except UnknownValidator:
        pass
    raise SchemingException('validator/converter not found: %r' % name)
