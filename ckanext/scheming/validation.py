from ckan.plugins.toolkit import get_validator, UnknownValidator

from ckanext.scheming.errors import SchemingException

OneOf = get_validator('OneOf')
ignore_missing = get_validator('ignore_missing')
not_missing = get_validator('not_missing')

def scheming_validator(fn):
    """
    Decorate a validator that needs to have the scheming fields
    passed with this function. When generating navl validator lists
    the function decorated will be called passing the field
    data to produce the actual validator for each field.
    """
    fn.is_a_scheming_validator = True
    return fn


@scheming_validator
def scheming_choices(field):
    """
    Require that one of the field choices values is passed.
    """
    return OneOf([c['value'] for c in field['choices']])


@scheming_validator
def scheming_required(field):
    """
    not_missing if field['required'] else ignore_missing
    """
    if field.get('required'):
        return not_missing
    return ignore_missing


def validators_from_string(s, field):
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
            v = v(field)
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
