from ckanext.scheming.validation import scheming_validator
from ckan.logic.validators import package_name_validator
import slugify
import copy
from ckantoolkit import (
    get_action,
    _
)


@scheming_validator
def scheming_shapefile(field, schema):
    """
    Verifies that the file uploaded is a zip-file with shapefiles
    """

    def shapefile_validator(key, data, errors, context):
        raise TypeError
        value = data.get(key)
        if ".zip" not in value:
            errors[key].extend(
                "Not a shapefile"
            )
    return shapefile_validator


@scheming_validator
def unique_combination(field, schema):
    def validator(key, data, errors, context):
        all_unique_comb_field_dicts = list(filter(
            lambda x: 'unique_combination' in x.get('validators', ''),
            schema['dataset_fields']
        ))
        field_names = [x['field_name'] for x in all_unique_comb_field_dicts]
        field_values = [data.get((x,)) for x in field_names]
        zipped_fields = zip(field_names, field_values)
        queries = [u"{}:\"{}\"".format(f[0], f[1]) for f in zipped_fields]
        query_string = u" AND ".join(queries)

        # Ensure uniqueness is only scoped to an organization
        if data.get(('owner_org',)):
            query_string += u" AND owner_org:{}".format(data[('owner_org',)])

        package = context.get('package')
        if package:
            package_id = package.id
        else:
            package_id = data.get(key[:-1] + ('id',))
        if package_id:
            query_string = u"{} AND NOT id:\"{}\"".format(
                query_string,
                package_id
            )

        results = get_action('package_search')({}, {'q': query_string})
        if results.get('count'):
            errors[key].append(
                _('A package already exists for: {}. Please update '
                  'existing package.').format(", ".join(field_values))
            )
            errors[('name',)] = []

    return validator


@scheming_validator
def auto_create_valid_name(field, schema):
    def validator(key, data, errors, context):
        counter = 1
        while True:
            package_name_errors = copy.deepcopy(errors)
            package_name_validator(key, data, package_name_errors, context)
            if package_name_errors[key] == errors[key]:
                break
            else:
                data[key] = "{}-{}".format(data[key], counter)
                counter = counter + 1
    return validator


@scheming_validator
def autogenerate(field, schema):
    template = field[u'template']
    template_args = field[u'template_args']
    template_formatters = field.get(u'template_formatters', dict())
    formatters = {
        "lower": __lower_formatter,
        "slugify": slugify.slugify,
        "comma_swap": __comma_swap_formatter
    }
    f_list = []
    for f in template_formatters:
        if f in formatters.keys():
            f_list.append(formatters[f])

    def validator(key, data, errors, context):
        str_args = []
        for t_arg in template_args:
            arg_value = data[(t_arg,)]
            for f in f_list:
                arg_value = f(arg_value)
            str_args.append(arg_value)
        auto_text = template.format(*str_args)
        data[key] = auto_text
        pass
    return validator


def __lower_formatter(input):
    return input.lower()


def __comma_swap_formatter(input):
    """
    Swaps the parts of a string around a single comma.
    Use to format e.g. "Tanzania, Republic of" as "Republic of Tanzania"
    """
    if input.count(',') == 1:
        parts = input.split(',')
        stripped_parts = map(lambda x: x.strip(), parts)
        reversed_parts = reversed(stripped_parts)
        joined_parts = " ".join(reversed_parts)
        return joined_parts
    else:
        return input
