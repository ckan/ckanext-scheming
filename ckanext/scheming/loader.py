"""
Load either yaml or json, based on the name of the resource
"""

import json
from functools import partial

try:
    import yaml
except ImportError:
    yaml = None

from ckanext.scheming.errors import LoaderError

YamlMissingError = partial(
    LoaderError,
    'PyYAML dependency is missing, unable to load YAML schema file.'
)


def load(f):
    if is_yaml(f.name):
        if yaml is None:
            raise YamlMissingError()
        return yaml.load(f)
    return json.load(f)


def loads(s, url):
    if is_yaml(url):
        if yaml is None:
            raise YamlMissingError()
        return yaml.load(s)
    return json.loads(s)


def is_yaml(n):
    return n[-5:].lower() == '.yaml' or n[-4:] == '.yml'
