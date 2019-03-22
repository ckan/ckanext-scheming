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
