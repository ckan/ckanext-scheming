#!/bin/bash
set -e

if [ $CKANVERSION == 'master' ]
then
    pytest --ckan-ini=subdir/test_subclass.ini ckanext/scheming/tests/test_dataset_display.py ckanext/scheming/tests/test_form.py::TestDatasetFormNew ckanext/scheming/tests/test_dataset_logic.py
    pytest --ckan-ini=subdir/test.ini --cov=ckanext.scheming
else
    nosetests --ckan --nologcapture --with-pylons=subdir/test_subclass.ini ckanext.scheming.tests.nose.test_dataset_display ckanext.scheming.tests.nose.test_form:TestDatasetFormNew ckanext.scheming.tests.nose.test_dataset_logic
    nosetests --ckan --nologcapture --with-pylons=subdir/test.ini --with-coverage --cover-package=ckanext.scheming --cover-inclusive --cover-erase --cover-tests ckanext/scheming/tests/nose

fi
