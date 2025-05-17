## 0.0.1

2014-09-08

* initial release


## 0.0.2

2014-12-01

* automated tests and coverage
* presets feature including: title, dataset_slug, tag_string_autocomplete,
  dataset_organization, resource_url_upload, resource_format_autocomplete,
  select presets


## 1.0.0

2015-10-14

* first stable release
* working group/org customization
* new presets: multiple_checkbox, multiple_select, date
* support for yaml schemas+presets
* lots of fixes


## 1.1.0

2017-10-05

* automated tests against ckan 2.4, 2.5 and 2.6
* json_object field preset for arbitrary JSON objects as values
* datetime and datetime_tz field presets for date+time validation
* display_snippet=null to hide fields from being displayed
* choices_helper option to use a helper function for custom choice lists
* scheming_datastore_choices helper for pulling choice lists from a
  DataStore table
* select_size option to customize select form snippet
* sorted_choices option to sort choices before displaying them
* automatic reloading on schema changes in development mode
* improved test coverage and lots of fixes


## 1.2.0

2019-03-22

* automated tests against 2.6, 2.7, 2.8 and master
* fixes and tests for group and org schemas
* form_attrs are now added to existing tag classes instead of replacing them
* remove delete button from create form
* support for custom types in the slug widget
* added required fields markers for groups/orgs
* allow hiding resource fields
* other small fixes


## 2.0.0

2020-04-24

* python 3 support (ckan 2.9+)
* automated tests against 2.6, 2.7, 2.8 and master now using pytest
* select_size option defaults to choices length
* form_snippet=null to hide form fields for group/org forms
* improved plugin reloading support
* add support for group/org image uploads
* other small fixes


## 2.1.0

2021-01-20

* repeating_subfields feature for repeating groups of dataset fields
* multiple_text preset added to support repating text fields
* automated tests against 2.7, 2.8, 2.9 and 2.9 under python 3
* examples converted to yaml for readability
* allow display of data dictionary
* fix auto-generation of resource names
* restore license options in 2.9
* add support for organization image uploads


## 3.0.0

2022-11-24

* dataset metadata forms may now be split across multiple pages with
  start_form_page
* new ckan_formpages.yaml example schema using dataset form pages
* datastore_additional_choices option for adding static choices
  to a dynamic choice list
* new markdown and radio field form snippets and presets
* automated tests against 2.8 (py2), 2.9 (py2), 2.9 and 2.10
* show extra resource fields on resource pages
* csrf_input and humanize_entity_type support for ckan 2.10
* improved documentation and examples
* fixes for multiple_text form fields
* fixes for repeating_subfields feature
* fix for applying default org/group types
* sync example dataset schemas, presets and templates with upstream ckan
  changes

## 3.1.0

2025-03-27

* This version drops support for CKAN 2.8, 2.9 and adds support for 2.11
* Pass dataset name to resource fields snippets [#437](https://github.com/ckan/ckanext-scheming/pull/354)
* Allow literal parameters in validator string [#372](https://github.com/ckan/ckanext-scheming/pull/372)
* Fix delete URL for custom organizations [#374](https://github.com/ckan/ckanext-scheming/pull/374)
* Group Form Required Message Position [#376](https://github.com/ckan/ckanext-scheming/pull/376)
* Resource Form Errors Super Fallback [#380](https://github.com/ckan/ckanext-scheming/pull/380)
* Use form_snippets/help_text.html in repeating_subfields.html [#387](https://github.com/ckan/ckanext-scheming/pull/397)
* Add form-select CSS class to select elements [#399](https://github.com/ckan/ckanext-scheming/pull/399)
* Fix ckan version comparison [#406](https://github.com/ckan/ckanext-scheming/pull/406)
* Add number and file_size snippets [#412](https://github.com/ckan/ckanext-scheming/pull/412)
* Before and After Validators for Groups [#428](https://github.com/ckan/ckanext-scheming/pull/428)
* Drop ckantoolkit requirement [#432](https://github.com/ckan/ckanext-scheming/pull/432)
* Fix `is_organization` for custom `organization_type` [#437](https://github.com/ckan/ckanext-scheming/pull/437), [#431](https://github.com/ckan/ckanext-scheming/pull/431)
* fix: Move toggle-more rows to bottom of resource table [#420](https://github.com/ckan/ckanext-scheming/pull/420)
* fix: Add default text to update/edit buttons in group_form [#421](https://github.com/ckan/ckanext-scheming/pull/421)
* fix: False is also a value for radio and select snippets [#417](https://github.com/ckan/ckanext-scheming/pull/417)
* Remove presets parsing cache check [#425](https://github.com/ckan/ckanext-scheming/pull/425)
* fix: optional multiple_text saved as empty string if missing on create
