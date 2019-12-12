# -*- coding: utf-8 -*-

from __future__ import print_function

import json
from six import StringIO

from ckanext.scheming.helpers import (
    scheming_dataset_schemas,
    scheming_group_schemas,
    scheming_organization_schemas,
    scheming_language_text,
)


def describe_schemas():
    schemas = [
        ("Dataset", scheming_dataset_schemas()),
        ("Group", scheming_group_schemas()),
        ("Organization", scheming_organization_schemas()),
    ]
    result = StringIO()
    for n, s in schemas:
        print(n, "schemas:", file=result)
        if s is None:
            print("\tplugin not loaded or schema not specified\n", file=result)
            continue
        if not s:
            print("\tno schemas", file=result)
        for typ in sorted(s):
            print(" * " + json.dumps(typ), file=result)
            field_names = ('dataset_fields', 'fields', 'resource_fields')

            for field_name in field_names:
                if s[typ].get(field_name):
                    if field_name == 'resource_fields':
                        print(" * " + json.dumps("resource"), file=result)
                    for field in s[typ][field_name]:
                        print("\t- " + json.dumps(field['field_name']),
                              end='\t',
                              file=result)
                        print(scheming_language_text(field.get('label')),
                              file=result)
        print(file=result)
    return result.getvalue()
