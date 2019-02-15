#!/bin/sh -e

nosetests --ckan --nologcapture --with-pylons=subdir/test_subclass.ini tests.test_dataset_display tests.test_form:TestDatasetFormNew tests.test_dataset_logic
nosetests --ckan --nologcapture --with-pylons=subdir/test.ini --with-coverage --cover-package=ckanext.scheming --cover-inclusive --cover-erase --cover-tests
