ckanext-scheming
================

This CKAN extension provides a way to configure and share metadata schemas using a
YAML or JSON schema description. Custom validation and template snippets for editing
and display are supported.

[![Travis](https://travis-ci.org/ckan/ckanext-scheming.svg?branch=master)](https://travis-ci.org/ckan/ckanext-scheming)
[![Coverage](https://coveralls.io/repos/ckan/ckanext-scheming/badge.svg?branch=master&service=github)](https://coveralls.io/github/ckan/ckanext-scheming?branch=master)

Requirements
============

This plugin is compatible with CKAN 2.6 or later.


Configuration
=============

Set the schemas you want to use with configuration options:

```ini
ckan.plugins = scheming_datasets

#   module-path:file to schemas being used
scheming.dataset_schemas = ckanext.spatialx:spatialx_schema.yaml
                           ckanext.spatialx:spatialxy_schema.yaml
#   will try to load "spatialx_schema.yaml" and "spatialxy_schema.yaml"
#   as dataset schemas
#
#   URLs may also be used, e.g:
#
# scheming.dataset_schemas = http://example.com/spatialx_schema.yaml

#   Preset files may be included as well. The default preset setting is:
scheming.presets = ckanext.scheming:presets.json

#   The is_fallback setting may be changed as well. Defaults to false:
scheming.dataset_fallback = false
```


Example dataset schemas
-----------------------

* [default dataset schema](ckanext/scheming/ckan_dataset.yaml)
* [camel photos schema](ckanext/scheming/camel_photos.yaml)

These schemas are included in ckanext-scheming and may be enabled
with e.g: `scheming.dataset_schemas = ckanext.scheming:camel_photos.yaml`

These schemas use [presets](#preset) defined in
[presets.json](ckanext/scheming/presets.json).


Schema Keys
-----------


### `scheming_version`

```yaml
scheming_version: 2
```

Use `scheming_version: 2` with ckanext-scheming version 2.0.0 or later.


### `dataset_type` / `group_type`

```yaml
dataset_type: camel-photos
```

This is the "type" field stored in the dataset.
It is also used to set the URL for searching this type of dataset.

Normal datasets would be available under the URL `/dataset`, but datasets with
the `camel_photos.json` schema above would appear under `/camel-photos` instead.


### `about_url`

```yaml
about_url: https://github.com/link-to-my-project
```

`about_url` is a Link to human-readable information about this schema.
Its use is optional but highly recommended.


### `dataset_fields`, `resource_fields`

```yaml
dataset_fields:

- field_name: title
  label: Title
  preset: title

- field_name: name
  label: URL
  preset: dataset_slug

...
```

Fields are specified in the order you
would like them to appear in the dataset and resource editing
pages.

Fields you exclude will not be shown to the end user, and will not
be accepted when editing or updating this type of dataset.


Field Keys
----------


### `field_name`

The `field_name` value is the name of an existing CKAN dataset or resource
field or a new extra field. Existing dataset
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

```yaml
label:
  en: Title
  fr: Titre
```

When using a plain string translations will be provided with gettext:

```yaml
label: Title
```


### `required`

Use `required: true` for fields that must be included. Set to `false` or
don't include this key for fields that are optional.

Setting to `true` will mark the field as required in the editing form
and include `not_empty` in the default validators that will be applied
when `validators` is not specified.

To honor this settings with custom validators include `scheming_required`
as the first validator. `scheming_required` will check the required
setting for this field and apply either the `not_empty` or `ignore_missing`
validator.


### `choices`

The `choices` list may be provided for
select and multiple choice fields.
List elements include `label`s for human-readable text for
each element (may be multiple languages like a [field label](#label))
and `value`s that will be stored in the dataset or resource:

```yaml
preset: select
choices:
- value: bactrian
  label: Bactrian Camel
- value: hybrid
  label: Hybrid Camel
```

### `choices_helper`

If a choices list is not provided you must provide a `choices_helper`
function that will return a list of choices in the same format as
the `choices` list above.

You may [register your own helper function](https://docs.ckan.org/en/2.8/theming/templates.html#adding-your-own-template-helper-functions) or use the
`scheming_datastore_choices` helper included in ckanext-scheming:

```yaml
preset: select
choices_helper: scheming_datastore_choices
datastore_choices_resource: countries-resource-id-or-alias
datastore_choices_columns:
  value: Country Code
  label: English Country Name
```


### `preset`

A `preset` specifies a set of default values for these field keys. They
are used to define validation and snippets for common field
types.

This extension includes the following presets:

* `preset: title` - title validation and large text form snippet
* `preset: select` - validation that choice is from [choices](#choices),
  form select box and display snippet
* `preset: multiple_checkbox` - multiple choice from [choices](#choices)
  rendered as checkboxes in the form
* `preset: multiple_select` - multiple choice from [choices](#choices)
  rendered as a multiple select box in the form
* `preset: date` - date validation and form snippet
* `preset: datetime` date and time validation and form snippet
* `preset: dataset_slug` - dataset slug validation and form snippet that
  autofills the value from the title field
* `preset: tag_string_autocomplete` - tag string validation and form autocomplete
* `preset: dataset_organization` - organization validation and form select box
* `preset: resource_url_upload` - resource url validaton and link/upload form
  field
* `preset: resource_format_autocomplete` - resource format validation with
  format guessing based on url and autocompleting form field
* `preset: json_object` - JSON based input. Only JSON objects are supported.
  The input JSON will be loaded during output (eg when loading the dataset in
  a template or via the API).


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

The included form snippets may be found under [templates/scheming/form_snippets](ckanext/scheming/templates/scheming/form_snippets).

### `display_snippet`

The `display_snippet` value is the name of the snippet template to
use for this field in the dataset, resource, group or organization view page.
A number of snippets are provided with this
extension, but you may also provide your own by creating templates
under `scheming/display_snippets/` in a template directory in your
own extension.

This snippet is passed the `field` dict containing all the keys and
values in this field record, including any additional ones
you added to your that aren't handled by this extension.

The included display snippets may be found under [templates/scheming/display_snippets](ckanext/scheming/templates/scheming/display_snippets).

If `display_snippet: null` is used the field will be removed from the view page.

### `select_size`

```yaml
select_size: 5
```

Set to the number of [choices](#choices) to display in the multiple_select
[form](#form_snippet) snippets.


### `sorted_choices`

Set to `"true"` to sort [choices](#choices) alphabetically in [form](#form_snippet)
and [display](#display_snippet) snippets.


### `validators`

The `validators` value is a space-separated string of validator and
converter functions to use for this field when creating or updating data.
When a validator name is followed by parenthesis the function is called
passing the comma-separated values within as string parameters
and the result is used as the validator/converter.

```yaml
validators: if_empty_same_as(name) unicode
```

is the same as a plugin using the validators:

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
lists available validators ready to be used.

### `output_validators`

The `output_validators` value is like `validators` but used when
retrieving values from the database instead of when saving them.
These validators may be used to transform the data before it is
sent to the user.

This extension automatically adds calls to `convert_from_extras`
for extra fields so you should not add that to this list.

### `create_validators`

The `create_validators` value if present overrides `validators` during
create only.

### `help_text`

Only if this key is supplied, its value will be shown as inline help text,
Help text must be plain text, no markdown or HTML are allowed.
Help text may be provided in multiple languages like [label fields](#label).

### `help_inline`

Display help text inline if set to `true`. Default is `false`.


Running the Tests
=================

To run the tests, do:

```nosetests --ckan --nologcapture --with-pylons=test.ini```

and

```nosetests --ckan --nologcapture --with-pylons=test_subclass.ini ckanext.scheming.tests.test_dataset_display ckanext.scheming.tests.test_form:TestDatasetFormNew ckanext.scheming.tests.test_dataset_logic```

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run:

```nosetests --ckan --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.scheming --cover-inclusive --cover-erase --cover-tests```
