ckanext-scheming
================

This CKAN extension provides a way to configure and share metadata schemas using a
YAML or JSON schema description. Custom validation and template snippets for editing
and display are supported.

[![Tests](https://github.com/ckan/ckanext-scheming/workflows/Tests/badge.svg?branch=master)](https://github.com/ckan/ckanext-scheming/actions)

Table of contents:

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
   - [Schema Types](#schema-types)
   - [Example Schemas](#example-schemas)
   - [Storing non-string data](#storing-non-string-data)
   - [Common Schema Keys](#common-schema-keys)
     - [`scheming_version`](#scheming_version)
     - [`about_url`](#about_url)
   - [Dataset Schema Keys](#dataset-schema-keys)
     - [`dataset_type`](#dataset_type)
     - [`dataset_fields`, `resource_fields`](#dataset_fields-resource_fields)
   - [Group / Organization Schema Keys](#group--organization-schema-keys)
     - [`group_type`](#group_type)
     - [`organization_type`](#organization_type)
     - [`fields`](#fields)
   - [Field Keys](#field-keys)
     - [`field_name`](#field_name)
     - [`label`](#label)
     - [`repeating_subfields`](#repeating_subfields)
     - [`start_form_page`](#start_form_page)
     - [`required`](#required)
     - [`choices`](#choices)
     - [`choices_helper`](#choices_helper)
     - [`preset`](#preset)
     - [`form_snippet`](#form_snippet)
     - [`display_snippet`](#display_snippet)
     - [`display_property`](#display_property)
     - [`validators`](#validators)
     - [`output_validators`](#output_validators)
     - [`create_validators`](#create_validators)
     - [`help_text`](#help_text)
4. [Action API Endpoints](#action-api-endpoints)
5. [Running the Tests](#running-the-tests)



Requirements
============

This plugin is compatible with CKAN 2.8 or later.


Installation
============

You can install the extension with the following shell commands:

```sh
cd $CKAN_VENV/src/

pip install -e "git+https://github.com/ckan/ckanext-scheming.git#egg=ckanext-scheming"
```


Configuration
=============

Set the schemas you want to use with configuration options:

```ini

# Each of the plugins is optional depending on your use
ckan.plugins = scheming_datasets scheming_groups scheming_organizations

#   module-path:file to schemas being used
scheming.dataset_schemas = ckanext.spatialx:spatialx_schema.yaml
                           ckanext.spatialx:spatialxy_schema.yaml
#   will try to load "spatialx_schema.yaml" and "spatialxy_schema.yaml"
#   as dataset schemas

#   For group and organization schemas (replace myplugin with your custom plugin)
scheming.group_schemas = ckanext.scheming:group_with_bookface.json
                         ckanext.myplugin:/etc/ckan/default/group_with_custom_fields.json
scheming.organization_schemas = ckanext.scheming:org_with_dept_id.json
                                ckanext.myplugin:org_with_custom_fields.json
#
#   URLs may also be used, e.g:
#
# scheming.dataset_schemas = http://example.com/spatialx_schema.yaml

#   The separator to use to flatten composite fields (repeating_subfields)
scheming.composite.separator = |

#   Preset files may be included as well. The default preset setting is:
scheming.presets = ckanext.scheming:presets.json

#   The is_fallback setting may be changed as well. Defaults to false:
scheming.dataset_fallback = false
```

## Schema Types
With this plugin, you can customize the group, organization, and dataset entities in CKAN. Adding and enabling a schema will modify the forms used to update and create each entity, indicated by the respective `type` property at the root level. Such as `group_type`, `organization_type`, and `dataset_type`. Non-default types are supported properly as is indicated throughout the examples.


## Example Schemas

Dataset schemas:

* [default dataset schema](ckanext/scheming/ckan_dataset.yaml)
* [camel photos schema](ckanext/scheming/camel_photos.yaml)
* [subfields schema](ckanext/scheming/subfields.yaml)
* [form pages schema](ckanext/scheming/ckan_formpages.yaml)

These schemas are included in ckanext-scheming and may be enabled
with e.g: `scheming.dataset_schemas = ckanext.scheming:camel_photos.yaml`

These schemas use [presets](#preset) defined in
[presets.json](ckanext/scheming/presets.json).

Group schemas:

* [Default group schema with field modifications](ckanext/scheming/group_with_bookface.json)
* [Group with custom type](ckanext/scheming/custom_group_with_status.json)

Organization schemas:

* [Default organization schema with field modifications](ckanext/scheming/org_with_dept_id.json)
* [Organization with custom type](ckanext/scheming/custom_org_with_address.json)



## Common Schema Keys

### `scheming_version`

Set to `2`. Future versions of ckanext-scheming may use a larger
number to indicate a change to the schema format.

### `about_url`

```yaml
about_url: https://github.com/link-to-my-project
```

`about_url` is a link to human-readable information about this schema.
ckanext-scheming [automatically publishes](#action-api-endpoints) your
schema and this link allows users to learn more about it.

## Dataset Schema Keys

### `dataset_type`

```yaml
dataset_type: camel-photos
```

This is the "type" field stored in the dataset.
It is also used to set the URL for searching this type of dataset.

Normal datasets would be available under the URL `/dataset`, but datasets with
the `camel_photos.json` schema above would appear under `/camel-photos` instead.


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




## Group / Organization Schema Keys

### `group_type`

```yaml
group_type: group
```
is used for modifying the default group schema

```yaml
group_type: theme
```
is an example of defining a custom group type, as seen in the [example schemas above](#example-schemas)

Like `dataset_type`, a `group_type` of `group` allows you to customize the default group schema under the URL `/group`, such as the modified schema in `group_with_bookface.json`, but a schema with a custom type such as `custom_group_with_status.json` schema above would appear under `/theme` instead, because its `group_type` field is set to "theme".

### `organization_type`

```yaml
organization_type: organization
```
is used for modifying the default organization schema

```yaml
organization_type: publisher
```
is an example of defining a custom organization type, as seen in the [example schemas above](#example-schemas)

### `fields`

```yaml
fields:

- field_name: title
  label: Name
  form_snippet: large_text.html
  form_attrs:
    data_module: slug-preview-target
  form_placeholder: My Organization

...
```
A single `fields` list replaces the `dataset_fields` and `resource_fields` schema properties doin dataset schemas.


----------------

## Field Keys
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


### `label`

The `label` value is a human-readable label for this field as
it will appear in the dataset editing form.
This label may be a string or an object providing multiple
language versions:

```yaml
- field_name: title
  label:
    en: Title
    fr: Titre
```

When using a plain string translations will be provided with gettext:

```yaml
- field_name: title
  label: Title
```


### `repeating_subfields`

This field is the parent of group of repeating subfields. The value is
a list of fields entered the same way as normal fields.

> **_NOTE:_** CKAN needs an IPackageController plugin with `before_index` to
> convert repeating subfields to formats that can be indexed by solr. For
> testing you may use the included `scheming_nerf_index` plugin to encode
> all repeating fields as JSON strings to prevent solr errors.

`repeating_label` may be used to provide a singular version of the label
for each group.

```yaml
- field_name: contacts
  label: Contacts
  repeating_label: Contact
  repeating_subfields:

  - field_name: address
    label: Address
    required: true

  - field_name: city
    label: City

  - field_name: phone
    label: Phone Number
```


### `start_form_page`

Dataset fields may be divided into separate form pages for creation
and editing. **_CKAN 2.9+ only_**. Form pages for `dataset` type
only supported by **_CKAN 2.10+_** or with https://github.com/ckan/ckan/pull/7032
. Adding `start_form_page` to a field marks this field as the start of a
new page of fields.


```yaml
- start_form_page:
    title: Detailed Metadata
    description:
      These fields improve search and give users important links

  field_name: address
  label: Address
```

A title and description should be provided to help with navigation.
These values may be strings or objects providing multiple
language versions of text.


### `required`

```yaml
  required: true
```

Use for fields that must be included. Set to `false` or
don't include this key for fields that are optional.

Setting to `true` will mark the field as required in the editing form
and include `not_empty` in the default validators that will be applied
when `validators` is not specified.

> **_NOTE:_** To honor this settings with custom validators include `scheming_required`
> as the first validator. `scheming_required` will check the required
> setting for this field and apply either the `not_empty` or `ignore_missing`
> validator.


### `choices`

The `choices` list may be provided for
select and multiple choice fields.
List elements include `label`s for human-readable text for
each element (may be multiple languages like a [field label](#label))
and `value`s that will be stored in the dataset or resource:

```yaml
- field_name: category
  preset: select
  choices:
  - value: bactrian
    label: Bactrian Camel
  - value: hybrid
    label: Hybrid Camel
```

For storing non-string values see [output_validators](#output_validators).

For required `select` fields you may also want to add this setting
so that users are forced to choose an item in the form, otherwise the first
choice will be selected in the form by default:

```yaml
  form_include_blank_choice: true
```

To set the number of choices displayed in the `multiple_select`
[form](#form_snippet) snippets use:

```yaml
  select_size: 5
```

To sort choices alphabetically in [form](#form_snippet)
and [display](#display_snippet) snippets use:

```yaml
  sorted_choices: true
```

### `choices_helper`

If a choices list is not provided you must provide a `choices_helper`
function that will return a list of choices in the same format as
the `choices` list above.

You may [register your own helper function](https://docs.ckan.org/en/2.8/theming/templates.html#adding-your-own-template-helper-functions) or use the
`scheming_datastore_choices` helper included in ckanext-scheming:

```yaml
- field_name: country
  preset: select
  choices_helper: scheming_datastore_choices
  datastore_choices_resource: countries-resource-id-or-alias
  datastore_choices_columns:
    value: Country Code
    label: English Country Name
  datastore_additional_choices:
  - value: none
    label: None
  - value: na
    label: N/A
```


### `preset`

A `preset` specifies a set of default values for other field keys. They
allow reuse of definitions for validation and snippets for common field types.

This extension includes the following presets in [presets.json](ckanext/scheming/presets.json):

```yaml
  preset: title
```
title validation and large text form snippet

```yaml
  preset: select
```
validation that choice is from [choices](#choices), form select box and display snippet

```yaml
  preset: radio
```
validation that choice is from [choices](#choices), form radio buttons group and display snippet

```yaml
  preset: multiple_checkbox
```
multiple choice from [choices](#choices) rendered as checkboxes in the form, stored as a list of values

```yaml
  preset: multiple_select
```
multiple choice from [choices](#choices) rendered as a multiple select box in the form, stored as a list of values

```yaml
  preset: multiple_text
```
repeating text field with add and remove buttons, stored as a list of strings

```yaml
  preset: date
```
date validation and form snippet

```yaml
  preset: datetime
```
date and time validation and form snippet

```yaml
  preset: dataset_slug
```
dataset slug validation and form snippet that autofills the value from the title field

```yaml
  preset: tag_string_autocomplete
```
tag string validation and form autocomplete

```yaml
  preset: dataset_organization
```
organization validation and form select box

```yaml
  preset: resource_url_upload
```
resource url validaton and link/upload form field

```yaml
  preset: resource_format_autocomplete
```
resource format validation and form autocomplete

```yaml
  preset: organization_url_upload
```
organization url validaton and link/upload form field
format guessing based on url and autocompleting form field

```yaml
  preset: json_object
```
JSON based input. Only JSON objects are supported. The input JSON will be loaded during output (eg when loading the dataset in a template or via the API

```yaml
  preset: markdown
```
markdown text area and display


You may define your own presets by adding additional files to the `scheming.presets`
[configuration setting](#configuration).


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

### `display_property`

```yaml
- field_name: author
  label: Author
  display_property: dc:creator
```

Set a `property` attribute on dataset fields displayed as "Additional Info", useful for adding RDF markup.

### `validators`

The `validators` value is a space-separated string of validator and converter
functions to use for this field when creating or updating data.  When a
validator name is followed by parenthesis the function is called passing the
comma-separated values within and the result is used as the
validator/converter.

```yaml
  validators: if_empty_same_as(name) unicode_safe
```

is the same as a plugin using the validators:

```python
[get_validator('if_empty_same_as')("name"), unicode_safe]
```

If parameters can be parsed as a valid python literals, they are passed with
original type. If not, all parameters passed as strings. In addition, space
character is not allowed in argument position. Use its HEX code instead `\\x20`.

```yaml
  validators: xxx(hello,world)    # xxx("hello", "world")
  validators: xxx(hello,1)        # xxx("hello", "1")
  validators: xxx("hello",1,None) # xxx("hello", 1, None)
  validators: xxx("hello\\x20world") # xxx("hello world")
```

This string does not contain arbitrary python code to be executed,
you may only use registered validator functions, optionally calling
them with static string values provided.

> **_NOTE:_** ckanext-scheming automatically adds calls to `convert_to_extras`
> for extra fields when required.

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

Internally all extra fields are stored as strings. If you are attempting to save and restore other types of data you will need to use output validators.

For example if you use a simple "yes/no" question, you will need to let ckanext-scheming know that this data needs to be stored *and retrieved* as a boolean. This is acheieved using [`validators`](#validators) and [`output_validators`](#output_validators) keys.

```
  - field_name: is_camel_friendly
    label: Is this camel friendly?
    required: true
    preset: select
    choices:
      - value: false
        label: "No"
      - value: true
        label: "Yes"
    validators: scheming_required boolean_validator
    output_validators: boolean_validator
```

The `output_validators` value is like `validators` but used when
retrieving values from the database instead of when saving them.
These validators may be used to transform the data before it is
sent to the user.

> **_NOTE:_** ckanext-scheming automatically adds calls to `convert_from_extras`
> for extra fields when required.

### `create_validators`

The `create_validators` value if present overrides `validators` during
create only.

### `help_text`

```yaml
  help_text: License definitions and additional information
```

If this key is supplied, its value will be shown after the field as help text.
Help text may be provided in multiple languages like [label fields](#label).

Help text must be plain text, no markdown or HTML are allowed unless:

```yaml
  help_allow_html: true
```

Allow HTML inside the help text if set to `true`. Default is `false`.

Adjust the position of `help_text` with:

```yaml
  help_inline: true
```

Display help text inline (next to the field) if set to `true`. Default is `false` (display help text under the field).

Action API Endpoints
====================

The extension adds action endpoints which expose any configured schemas via:
https://github.com/ckan/ckanext-scheming/blob/master/ckanext/scheming/logic.py

Some examples:

Calling `http://localhost:5000/api/3/action/scheming_dataset_schema_list`

Returns:

```
{
  help: "http://localhost:5005/api/3/action/help_show?name=scheming_dataset_schema_list",
  success: true,
  result: [
    "dataset",
    "camel-photos"
  ]
}
```

Calling `http://localhost:5000/api/3/action/scheming_dataset_schema_show?type=dataset`

Returns:

```
{
  help: "http://localhost:5005/api/3/action/help_show?name=scheming_dataset_schema_show",
  success: true,
  result: {
    scheming_version: 2,
    dataset_type: "dataset",
    about: "A reimplementation of the default CKAN dataset schema",
    about_url: "http://github.com/ckan/ckanext-scheming",
    dataset_fields: [...],
    resource_fields: [...]
  }
}
```

The full list of API actions are available in [ckanext/scheming/logic.py](https://github.com/ckan/ckanext-scheming/blob/master/ckanext/scheming/logic.py)


Running the Tests
=================


To run the tests:

    pytest --ckan-ini=test.ini ckanext/scheming/tests
