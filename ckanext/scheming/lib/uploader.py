# encoding: utf-8
import cgi
import logging
import os

import ckan.lib.munge as munge
import ckan.logic as logic
from ckan.lib.uploader import get_storage_path
from werkzeug.datastructures import FileStorage as FlaskFileStorage

ALLOWED_UPLOAD_TYPES = (cgi.FieldStorage, FlaskFileStorage)
MB = 1 << 20

log = logging.getLogger(__name__)

_storage_path = None
_max_resource_size = None
_max_image_size = None


def _copy_file(input_file, output_file, max_size):
    input_file.seek(0)
    current_size = 0
    while True:
        current_size = current_size + 1
        # MB chunks
        data = input_file.read(MB)

        if not data:
            break
        output_file.write(data)
        if current_size > max_size:
            raise logic.ValidationError({'upload': ['File upload too large']})


def _get_underlying_file(wrapper):
    if isinstance(wrapper, FlaskFileStorage):
        return wrapper.stream
    return wrapper.file


def _make_dirs_if_not_existing(storage_path):
    try:
        os.makedirs(storage_path)
    except OSError as e:
        # errno 17 is file already exists
        if e.errno != 17:
            raise


class OrganizationUploader(object):
    def __init__(self, object_type, old_filename=None):
        """ Setup upload by creating a subdirectory of the storage directory
        of name object_type. old_filename is the name of the file in the url
        field last time"""

        self.storage_path = None
        self.filename = None
        self.filepath = None
        path = get_storage_path()
        if not path:
            return
        self.storage_path = os.path.join(path, 'storage', 'uploads', 'organization')
        _make_dirs_if_not_existing(self.storage_path)
        self.object_type = object_type
        self.old_filename = old_filename
        self.old_filepath = None

    def update_data_dict(self, data_dict, url_field, file_field, clear_field):
        """ Manipulate data from the data_dict.  url_field is the name of the
        field where the upload is going to be. file_field is name of the key
        where the FieldStorage is kept (i.e the field where the file data
        actually is). clear_field is the name of a boolean field which
        requests the upload to be deleted.  This needs to be called before
        it reaches any validators"""

        self.url = data_dict.get(url_field, '')
        self.clear = data_dict.pop(clear_field, None)
        self.file_field = file_field
        self.upload_field_storage = data_dict.pop(file_field, None)

        if not self.storage_path:
            return

        if self.old_filename:
            self.old_filepath = os.path.join(self.storage_path, data_dict.get('name'), self.old_filename)

        if isinstance(self.upload_field_storage, (ALLOWED_UPLOAD_TYPES)):
            self.filename = self.upload_field_storage.filename
            self.filename = munge.munge_filename(self.filename)
            organization_storagepath = os.path.join(self.storage_path, data_dict.get('name'))
            _make_dirs_if_not_existing(organization_storagepath)
            self.filepath = os.path.join(organization_storagepath, self.filename)
            data_dict[url_field] = self.filename
            data_dict['url_type'] = 'upload'
            self.upload_file = _get_underlying_file(self.upload_field_storage)
            self.tmp_filepath = self.filepath + '~'
        # keep the file if there has been no change
        elif self.old_filename and not self.old_filename.startswith('http'):
            if not self.clear:
                data_dict[url_field] = self.old_filename
            if self.clear and self.url == self.old_filename:
                data_dict[url_field] = ''

    def upload(self, max_size=2):
        """ Actually upload the file.
        This should happen just before a commit but after the data has
        been validated and flushed to the db. This is so we do not store
        anything unless the request is actually good.
        max_size is size in MB maximum of the file"""

        if self.filename:
            with open(self.tmp_filepath, 'wb+') as output_file:
                try:
                    _copy_file(self.upload_file, output_file, max_size)
                except logic.ValidationError:
                    os.remove(self.tmp_filepath)
                    raise
                finally:
                    self.upload_file.close()
            os.rename(self.tmp_filepath, self.filepath)
            self.clear = True

        if (self.clear and self.old_filename
                and not self.old_filename.startswith('http')):
            try:
                os.remove(self.old_filepath)
            except OSError:
                pass
