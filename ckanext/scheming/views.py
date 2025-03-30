
from flask import Response, Blueprint
from flask.views import MethodView
from werkzeug.datastructures import MultiDict

from ckan.plugins.toolkit import (
    h, request, get_action, abort, _, ObjectNotFound, NotAuthorized,
    ValidationError,
)
from ckan.plugins import PluginImplementations
try:
    from ckan.plugins import IFormRedirect
except ImportError:
    IFormRedirect = None

from ckan.views.dataset import CreateView, EditView

# FIXME these not available from toolkit
from ckan.lib.navl.dictization_functions import unflatten, DataError
from ckan.logic import clean_dict, tuplize_dict, parse_params


def _clean_page(package_type, page):
    '''return int page or raise ValueError if invalid for package_type'''
    page = int(page)
    if page < 1 or len(h.scheming_get_dataset_form_pages(package_type)) < page:
        raise ValueError('page number out of range')
    return page


class SchemingCreateView(CreateView):
    '''
    View for creating datasets with form pages
    '''
    def post(self, package_type):
        rval = super(SchemingCreateView, self).post(package_type)
        if getattr(rval, 'status_code', None) == 302:
            # successful create, send to page 2 instead of resource new page
            return h.redirect_to(
                '{}.scheming_new_page'.format(package_type),
                id=request.form['name'],
                page=2,
            )
        return rval


class SchemingCreatePageView(CreateView):
    '''
    Handle dataset form pages using package_patch
    '''
    def get(self, package_type, id, page):
        try:
            page = _clean_page(package_type, page)
        except ValueError:
            return abort(404, _('Page not found'))
        try:
            data = get_action('package_show')(None, {'id': id})
        except (NotAuthorized, ObjectNotFound):
            return abort(404, _('Dataset not found'))

        data['_form_page'] = page
        return super(SchemingCreatePageView, self).get(package_type, data)

    def post(self, package_type, id, page):
        try:
            page = _clean_page(package_type, page)
        except ValueError:
            return abort(404, _('Page not found'))
        try:
            data = get_action('package_show')(None, {'id': id})
        except (NotAuthorized, ObjectNotFound):
            return abort(404, _('Dataset not found'))

        # BEGIN: roughly copied from ckan/views/dataset.py
        try:
            data_dict = clean_dict(
                unflatten(tuplize_dict(parse_params(request.form)))
            )
        except DataError:
            return abort(400, _(u'Integrity Error'))
        save_action = data_dict.pop('save', None)
        data_dict.pop('pkg_name', None)
        data_dict['state'] = 'draft'
        # END: roughly copied from ckan/views/dataset.py

        data_dict['id'] = id
        try:
            complete_data = get_action('package_patch')(None, data_dict)
        except ObjectNotFound:
            return abort(404, _('Dataset not found'))
        except NotAuthorized:
            return abort(403, _(u'Unauthorized to update a dataset'))
        except ValidationError as e:
            # BEGIN: roughly copied from ckan/views/dataset.py
            errors = e.error_dict
            error_summary = e.error_summary
            data_dict[u'state'] = data[u'state']
            data_dict['_form_page'] = page

            return EditView().get(
                package_type,
                id,
                data_dict,
                errors,
                error_summary
            )
            # END: roughly copied from ckan/views/dataset.py

        if page == len(h.scheming_get_dataset_form_pages(package_type)):
            if IFormRedirect:
            # BEGIN: roughly copied from ckan/views/dataset.py
                for plugin in PluginImplementations(IFormRedirect):
                    url = plugin.dataset_save_redirect(
                        package_type, complete_data['name'], 'create',
                        save_action, data_dict)
                    if url:
                        return h.redirect_to(url)

            if 'resource_fields' in h.scheming_get_dataset_schema(package_type):
                return h.redirect_to(
                    '{}_resource.new'.format(package_type),
                    id=data['name'],
                )
            return h.redirect_to(
                '{}.read'.format(package_type),
                id=data['name'],
            )
            # END: roughly copied from ckan/views/dataset.py

        return h.redirect_to(
            '{}.scheming_new_page'.format(package_type),
            id=complete_data['name'],
            page=page + 1,
        )


def edit(package_type, id):
    if h.scheming_get_dataset_form_pages(package_type):
        return h.redirect_to(
            '{}.scheming_edit_page'.format(package_type),
            id=id,
            page=1
        )
    return EditView().get(package_type, id)


class SchemingEditPageView(EditView):
    '''
    Handle dataset form pages using package_patch
    '''
    def get(self, package_type, id, page):
        try:
            page = _clean_page(package_type, page)
        except ValueError:
            return abort(404, _('Page not found'))
        try:
            data = get_action('package_show')(None, {'id': id})
        except (NotAuthorized, ObjectNotFound):
            return abort(404, _('Dataset not found'))

        return super(SchemingEditPageView, self).get(package_type, id, {'_form_page':page})

    def post(self, package_type, id, page):
        try:
            page = _clean_page(package_type, page)
        except ValueError:
            return abort(404, _('Page not found'))
        try:
            data = get_action('package_show')(None, {'id': id})
        except (NotAuthorized, ObjectNotFound):
            return abort(404, _('Dataset not found'))

        # BEGIN: roughly copied from ckan/views/dataset.py
        try:
            data_dict = clean_dict(
                unflatten(tuplize_dict(parse_params(request.form)))
            )
        except DataError:
            return abort(400, _(u'Integrity Error'))

        try:
            data_dict.pop('_ckan_phase', None)
            data_dict.pop('save', None)
            data_dict['id'] = id
            # END: roughly copied from ckan/views/dataset.py
            save_action = 'save'
            if page == len(h.scheming_get_dataset_form_pages(package_type)):
                data_dict['state'] = 'active'
            complete_data = get_action('package_patch')(
                {'allow_state_change': True}, data_dict)

            if page < len(h.scheming_get_dataset_form_pages(package_type)):
                url = h.url_for(
                    f'{package_type}.scheming_edit_page', id=id,
                    page=page + 1)
                return h.redirect_to(url)

            # BEGIN: roughly copied from ckan/views/dataset.py
            for plugin in PluginImplementations(IFormRedirect):
                url = plugin.dataset_save_redirect(
                    package_type, complete_data['name'], 'edit', save_action,
                    complete_data)
                if url:
                    return h.redirect_to(url)

            url = h.url_for('{0}.read'.format(package_type), id=id)
            return h.redirect_to(url)

        except NotAuthorized:
            return abort(403, _(u'Unauthorized to update a dataset'))
        except ObjectNotFound:
            return abort(404, _('Dataset not found'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            data_dict[u'state'] = data[u'state']
            data_dict['_form_page'] = page

            return EditView().get(
                package_type,
                id,
                data_dict,
                errors,
                error_summary
            )
        # END: roughly copied from ckan/views/dataset.py
