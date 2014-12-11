ckanext-scheming
================

This extension provides a way to configure and share
CKAN schemas using a JSON schema description. Custom
template snippets for editing and display are also supported.

[![Build Status](https://travis-ci.org/open-data/ckanext-scheming.svg?branch=master)](https://travis-ci.org/open-data/ckanext-scheming)
[![Coverage](https://img.shields.io/coveralls/open-data/ckanext-scheming.svg?branch=master)](https://coveralls.io/r/open-data/ckanext-scheming)


Requirements
============

This plugin relies on the latest master branch
of ckan (including at least commit e909360) or
the upcoming 2.3 release of ckan


Configuration
=============

Set the schemas you want to use with configuration options:

```ini
ckan.plugins = scheming_datasets

#   module-path:file to schemas being used
scheming.dataset_schemas = ckanext.spatialx:spatialx_schema.json
                           ckanext.spatialx:spatialxy_schema.json
#   will try to load "spatialx_schema.json" and "spatialxy_schema.json"
#   as dataset schemas
#
#   URLs may also be used, e.g:
#
# scheming.dataset_schemas = http://example.com/spatialx_schema.json

#   Preset files may be included as well. The default preset setting is:
scheming.presets = ckanext.scheming:presets.json

#   The is_fallback setting may be changed as well. Defaults to false:
scheming.dataset_fallback = false
```


Example dataset schemas
-----------------------

* [default dataset schema](ckanext/scheming/ckan_dataset.json)
* [camel photos schema](ckanext/scheming/camel_photos.json)

These schemas are included in ckanext-scheming and may be enabled
with e.g: `scheming.dataset_schemas = ckanext.scheming:camel_photos.json`

These schemas use [presets](#preset) defined in
[presets.json](ckanext/scheming/presets.json).


Schema Keys
-----------


### `scheming_version`

Set to `1`. Future versions of ckanext-scheming may use a larger
number to indicate a change to the description JSON format.


### `dataset_type`

This is the "type" field stored in the dataset.
It is also used to set the URL for searching this type of dataset.

Normal datasets would be available under the URL `/dataset`, but datasets with
the `camel_photos.json` schema above would appear under `/camel-photos` instead.


### `about_url`

`about_url` is a Link to human-readable information about this schema.
Its use is optional but highly recommended.


### `dataset_fields`, `resource_fields`

Fields are specified in the order you
would like them to appear in the dataset and resource editing
pages.

Fields you exclude will not be shown to the end user, and will not
be accepted when editing or updating this type of dataset.


Field Keys
----------


### `field_name`

The `field_name` value is the name of an existing CKAN dataset or resource
field or a new new extra field. Existing dataset
field names include:

* `name` - the URI for the dataset
* `title`
* `notes` - the dataset description
* `author`
* `author_email`
* `maintainer`
* `maintainer_email`

New field names should follow the current lowercase_with_underscores
 naming convention. Don't name your field `mySpecialField`, use
 `my_special_field` instead.

This value is available to the form snippet as `field.field_name`.


### `label`

The `label` value is a human-readable label for this field as
it will appear in the dataset editing form.
This label may be a string or an object providing multiple
language versions:

```json
{
  "label": {
    "en": "Title",
    "fr": "Titre"
  },
  "...": "..."
}
```

When using a plain string translations will be provided with gettext:

```json
{
  "label": "Title",
  "...": "..."
}
```


### `required`

Set to `true` for fields that must be included. Set to `false` or
don't include this key for fields that are optional.

Setting to `true` will mark the field as required in the editing form
and include `not_empty` in the default validators that will be applied
when `validators` is not specified.

To honor this settings with custom validators include `scheming_required`
as the first validator. `scheming_required` will check the required
setting for this field and apply either the `not_empty` or `ignore_missing`
validator.


### `choices`

The `choices` list must be provided for
select fields.  List elements include `label`s for human-readable text for
each element (may be multiple languages like a [field label](#label))
and `value`s that will be stored in the dataset or resource:

```json
{
  "preset": "select",
  "choices": [
    {
      "value": "bactrian",
      "label": "Bactrian Camel"
    },
    "..."
  ],
  "...": "..."
}
```


### `preset`

A `preset` specifies a set of default values for these field keys. They
are typically used to define validation and snippets for common field
types.

This extension includes the following presets:

* `"title"` - title validation and large text form snippet
* `"select"` - validation that choice is from [choices](#choices),
  form select box and display snippet
* `"dataset_slug"` - dataset slug validation and form snippet that
  autofills the value from the title field
* `"tag_string_autocomplete"` - tag string validation and form autocomplete
* `"dataset_organization"` - organization validation and form select box
* `"resource_url_upload"` - resource url validaton and link/upload form
  field
* `"resource_format_autocomplete"` - resource format validation with
  format guessing based on url and autocompleting form field

You may add your own presets by adding them to the `scheming.presets`
configuration setting.


### `form_snippet`

The `form_snippet` value is the name of the snippet template to
use for this field in the dataset or resource editing form.
A number of snippets are provided with this
extension, but you may also provide your own by creating templates
under `scheming/form_snippets/` in a template directory in your
own extension.

This snippet is passed the `field` dict containing all the keys and
values in this field record, including any additional ones
you added to your that aren't handled by this extension.

This extension includes the following form snippets:

* [text.html](ckanext/scheming/templates/scheming/form_snippets/text.html) -
  a simple text field for free-form text or numbers (default)
* [large_text.html](ckanext/scheming/templates/scheming/form_snippets/large_text.html) -
  a larger text field, typically used for the title
* [date.html](ckanext/scheming/templates/scheming/form_snippets/date.html) -
  a date widget with a drop-down date picker - don't forget to use the `isodate` validator
* [slug.html](ckanext/scheming/templates/scheming/form_snippets/slug.html) -
  the default name (URL) field
* [license.html](ckanext/scheming/templates/scheming/form_snippets/license.html) -
  a dataset license selection field
* [markdown.html](ckanext/scheming/templates/scheming/form_snippets/markdown.html) -
  a markdown field, often used for descriptions
* [organization.html](ckanext/scheming/templates/scheming/form_snippets/organization.html) -
  an organization selection field for datasets
* [upload.html](ckanext/scheming/templates/scheming/form_snippets/upload.html) -
  an upload field for resource files
* [select.html](ckanext/scheming/templates/scheming/form_snippets/select.html) -
  a select box


### `display_snippet`

The `display_snippet` value is the name of the snippet template to
use for this field in the dataset, group or organization view page.
A number of snippets are provided with this
extension, but you may also provide your own by creating templates
under `scheming/display_snippets/` in a template directory in your
own extension.

This snippet is passed the `field` dict containing all the keys and
values in this field record, including any additional ones
you added to your that aren't handled by this extension.

This extension includes the following display snippets:

* [text.html](ckanext/scheming/templates/scheming/display_snippets/text.html) -
  render as a normal text value (default)
* [link.html](ckanext/scheming/templates/scheming/display_snippets/link.html) -
  render as an external link to open in a new window
* [email.html](ckanext/scheming/templates/scheming/display_snippets/email.html) -
  render as a "mailto:" link


### `validators`

The `validators` value is a space-separated string of validator and
converter functions to use for this field when creating or updating data.
When a validator name is followed by parenthesis the function is called
passing the comma-separated values within as string parameters
and the result is used as the validator/converter.

e.g. `"if_empty_same_as(name) unicode"` is the same as in a plugin specifying:

```python
[get_validator('if_empty_same_as')("name"), unicode]
```

This string does not contain arbitrary python code to be executed,
you may only use registered validator functions, optionally calling
them with static string values provided.

This extension automatically adds calls to `convert_to_extras`
for new extra fields,
so you should not add that to this list.

New validators and converters may be added using the
[IValidators plugin interface](http://docs.ckan.org/en/latest/extensions/plugin-interfaces.html?highlight=ivalidator#ckan.plugins.interfaces.IValidators).

Validators that need access to other values in this schema (e.g.
to test values against the choices list) may be decorated with
the [scheming.validation.scheming_validator](ckanext/scheming/validation.py)
function. This decorator will make scheming pass this field dict to the
validator and use its return value for validation of the field.

CKAN's [validator functions reference](http://docs.ckan.org/en/latest/extensions/validators.html) 
lists available validators ready to be used. E.g., date fields using the form snippet
[date.html](ckanext/scheming/templates/scheming/form_snippets/date.html)
should use the validator [isodate](http://docs.ckan.org/en/latest/extensions/validators.html#ckan.logic.validators.isodate).
In this specific case, the `isodate` validator will reject non-ISO8601 values
from older browsers, which might not be able to render the date picker widget
correctly, and default to a text field.


```json
{
    "field_name": "a_relevant_date",
    "label": "A relevant date",
    "help_text": "An example of a date field",
    "form_snippet": "date.html",
    "validators": "ignore_missing unicode isodate"
},
...
```

### `output_validators`

The `output_validators` value is like `validators` but used when
retrieving values from the database instead of when saving them.
These validators may be used to transform the data before it is
sent to the user.

This extension automatically adds calls to `convert_from_extras`
for extra fields so you should not add that to this list.

### `help_text`
         
Only if this key is supplied, its value will be shown as inline help text,
Help text must be plain text, no markdown or HTML are allowed.
