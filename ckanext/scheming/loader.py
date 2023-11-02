"""
Load either yaml or json, based on the name of the resource
"""

import json

def load(f):
    if is_yaml(f.name):
        import yaml
        return yaml.safe_load(f)
    return json.load(f)

def loads(s, url):
    if is_yaml(url):
        import yaml
        return yaml.safe_load(s)
    return json.loads(s)

def is_yaml(n):
    return n.lower().endswith(('.yaml', '.yml'))
