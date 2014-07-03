from ckan.plugins.toolkit import toolkit

from ckanext.scheming.errors import SchemingException


def validators_from_string(s):
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
            v = get_validator_or_converter(name)
            out.append(v(*args))
        else:
            out.append(get_validator_or_converter(p))
    return out


def get_validator_or_converter(name):
    """
    Get a validator or converter by name
    """
    if name == 'unicode':
        return unicode
    try:
        v = toolkit.get_validator(name)
        return v
    except KeyError:
        pass
    try:
        v = toolkit.get_converter(name)
        return v
    except KeyError:
        pass
    raise SchemingException('validator/converter not found: %r' % name)
