ckanext-scheming
================

This CKAN extension provides a way to configure and share metadata schemas using a
YAML or JSON schema description. Custom validation and template snippets for editing
and display are supported.

[![Tests](https://github.com/ckan/ckanext-scheming/workflows/Tests/badge.svg?branch=master)](https://github.com/ckan/ckanext-scheming/actions)


Requirements
============

This plugin is compatible with CKAN 2.6 or later.


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

#   Preset files may be included as well. The default preset setting is:
scheming.presets = ckanext.scheming:presets.json

#   The is_fallback setting may be changed as well. Defaults to false:
scheming.dataset_fallback = false
```

## Different Types of Schemas
With this plugin, you can customize the group, organization, and dataset entities in CKAN. Adding and enabling a schema will modify the forms used to update and create each entity, indicated by the respective `type` property at the root level. Such as `group_type`, `organization_type`, and `dataset_type`. Non-default types are supported properly in **CKAN 2.8+ only** as is indicated throughout the examples.

**Creating custom group or organization types is only supported in CKAN 2.8, instructions for that are below**


-------------------------------------------------------------------------------------
### Top-level Schema Keys (Common among dataset, group, and organization schemas)
#### `scheming_version`

Set to `2`. Future versions of ckanext-scheming may use a larger
number to indicate a change to the schema format.

#### `about_url`

`about_url` is a Link to human-readable information about this schema.
Its use is optional but highly recommended.

-------------------------------
### Example Schemas - Datasets

* [default dataset schema](ckanext/scheming/ckan_dataset.yaml)
* [camel photos schema](ckanext/scheming/camel_photos.yaml)
* [subfields schema](ckanext/scheming/subfields.yaml)

These schemas are included in ckanext-scheming and may be enabled
with e.g: `scheming.dataset_schemas = ckanext.scheming:camel_photos.yaml`

These schemas use [presets](#preset) defined in
[presets.json](ckanext/scheming/presets.json).


### Schema Keys - Datasets

```yaml
scheming_version: 2
```

Use `scheming_version: 2` with ckanext-scheming version 2.0.0 or later.


#### `dataset_type` / `group_type`

```yaml
dataset_type: camel-photos
```

This is the "type" field stored in the dataset.
It is also used to set the URL for searching this type of dataset.

Normal datasets would be available under the URL `/dataset`, but datasets with
the `camel_photos.json` schema above would appear under `/camel-photos` instead.


#### `about_url`

```yaml
about_url: https://github.com/link-to-my-project
```

`about_url` is a Link to human-readable information about this schema.
Its use is optional but highly recommended.


#### `dataset_fields`, `resource_fields`

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

---------------------------
### Example Schemas - Group

* [Default group schema with field modifications](ckanext/scheming/group_with_bookface.json)
* [Group with custom type **(CKAN 2.8+ only)**](ckanext/scheming/custom_group_with_status.json)


### Example Schemas - Organization

* [Default organization schema with field modifications](ckanext/scheming/org_with_dept_id.json)
* [Organization with custom type **(CKAN 2.8+ only)**](ckanext/scheming/custom_org_with_address.json)


### Schema Keys - Groups / Organization

#### `group_type`
Examples:
* `"group_type": "group"` used for modifying the default group schema
* `"group_type": "theme"` an example of defining a custom group type, as seen in the above examples **(CKAN 2.8+ only)**

#### `organization_type`
Examples:
* `"organization_type": "organization"` used for modifying the default organization schema
* `"organization_type": "publisher"` an example of defining a custom organization type, as seen in the above examples **(CKAN 2.8+ only)**

#### `fields`
The `dataset_fields` and `resource_fields` schema properties don't exist in group or organization schemas. Instead, they just have a `fields` property.

#### URLs
Like `dataset_type`, a `group_type` of `group` allows you to customize the default group schema under the URL `/group`, such as the modified schema in group_with_bookface.json, but a schema with a custom type **(CKAN 2.8+ only)** such as `custom_group_with_status.json` schema above would appear under `/theme` instead, because its `group_type` field is set to "theme".


----------------
### Field Keys
#### `field_name`

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


#### `label`

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


#### `repeating_subfields`

This field is the parent of group of repeating subfields. The value is
a list of fields entered the same way as normal fields. **CKAN 2.8+ only**

CKAN needs an IPackageController plugin with `before_index` to
convert repeating subfields to formats that can be indexed by solr. For
testing you may use the included `scheming_nerf_index` plugin to encode
all repeating fields as JSON strings to prevent solr errors.

`repeating_label` may be used to provide a singular version of the label
for each group.

```yaml
field_name: contacts
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


#### `required`

Use `required: true` for fields that must be included. Set to `false` or
don't include this key for fields that are optional.

Setting to `true` will mark the field as required in the editing form
and include `not_empty` in the default validators that will be applied
when `validators` is not specified.

To honor this settings with custom validators include `scheming_required`
as the first validator. `scheming_required` will check the required
setting for this field and apply either the `not_empty` or `ignore_missing`
validator.


#### `choices`

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

#### `choices_helper`

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
datastore_additional_choices:
- value: none
  label: None
- value: na
  label: N/A
```


#### `preset`

A `preset` specifies a set of default values for these field keys. They
are used to define validation and snippets for common field
types.

This extension includes the following presets:

* `preset: title` - title validation and large text form snippet
* `preset: select` - validation that choice is from [choices](#choices),
  form select box and display snippet
* `preset: radio` - validation that choice is from [choices](#choices),
  form radio buttons group and display snippet
* `preset: multiple_checkbox` - multiple choice from [choices](#choices)
  rendered as checkboxes in the form, stored as a list of values
* `preset: multiple_select` - multiple choice from [choices](#choices)
  rendered as a multiple select box in the form, stored as a list of values
* `preset: multiple_text` - repeating text field with add and remove
  buttons, stored as a list of strings
* `preset: date` - date validation and form snippet
* `preset: datetime` date and time validation and form snippet
* `preset: dataset_slug` - dataset slug validation and form snippet that
  autofills the value from the title field
* `preset: tag_string_autocomplete` - tag string validation and form autocomplete
* `preset: dataset_organization` - organization validation and form select box
* `preset: resource_url_upload` - resource url validaton and link/upload form
  field
* `preset: resource_format_autocomplete` - resource format validation with
* `preset: organization_url_upload` - organization url validaton and link/upload form
  field
  format guessing based on url and autocompleting form field
* `preset: json_object` - JSON based input. Only JSON objects are supported.
  The input JSON will be loaded during output (eg when loading the dataset in
  a template or via the API).
* `preset: markdown` - markdown text area and display


You may add your own presets by adding them to the `scheming.presets`
configuration setting.


#### `form_snippet`

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

#### `display_snippet`

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

#### `display_property`

```yaml
- field_name: author
  label: Author
  display_property: dc:creator
```

Set a `property` attribute on dataset fields displayed as "Additional Info", useful for adding RDF markup.

#### `select_size`

```yaml
select_size: 5
```

Set to the number of [choices](#choices) to display in the multiple_select
[form](#form_snippet) snippets.


#### `sorted_choices`

Set to `"true"` to sort [choices](#choices) alphabetically in [form](#form_snippet)
and [display](#display_snippet) snippets.


#### `validators`

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

#### `output_validators`

The `output_validators` value is like `validators` but used when
retrieving values from the database instead of when saving them.
These validators may be used to transform the data before it is
sent to the user.

This extension automatically adds calls to `convert_from_extras`
for extra fields so you should not add that to this list.

#### `create_validators`

The `create_validators` value if present overrides `validators` during
create only.

#### `help_text`

Only if this key is supplied, its value will be shown as inline help text,
Help text must be plain text, no markdown or HTML are allowed.
Help text may be provided in multiple languages like [label fields](#label).

#### `help_allow_html`

Allow HTML inside the help text if set to `true`. Default is `false`.

#### `help_inline`

Display help text inline if set to `true`. Default is `false`.

Action API Endpoints
====================

The extension adds action endpoints which expose any configured schemas via:
https://github.com/ckan/ckanext-scheming/blob/master/ckanext/scheming/logic.py

Some examples:

Calling http://localhost:5000/api/3/action/scheming_dataset_schema_list

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

Individual datasets can be called via [data_dict](https://docs.ckan.org/en/latest/maintaining/datastore.html#data-dictionary).

Calling http://localhost:5000/api/3/action/scheming_dataset_schema_show?type=dataset

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
