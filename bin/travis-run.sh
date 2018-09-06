#!/bin/sh -e

nosetests --ckan --nologcapture --with-pylons=subdir/test_subclass.ini ckanext.scheming.tests.test_dataset_display ckanext.scheming.tests.test_form:TestDatasetFormNew ckanext.scheming.tests.test_dataset_logic
nosetests --ckan --nologcapture --with-pylons=subdir/test.ini --with-coverage --cover-package=ckanext.scheming --cover-inclusive --cover-erase --cover-tests ckanext/scheming
