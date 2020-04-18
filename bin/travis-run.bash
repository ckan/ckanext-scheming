#!/bin/bash
set -e

pytest --ckan-ini=subdir/test.ini --cov=ckanext.scheming ckanext/scheming/tests
pytest --ckan-ini=subdir/test_subclass.ini ckanext/scheming/tests/test_dataset_display.py ckanext/scheming/tests/test_form.py::TestDatasetFormNew ckanext/scheming/tests/test_dataset_logic.py
