from ckan.lib.cli import CkanCommand
import ckan.plugins as p
import paste.script

from ckanext.scheming.plugins import (SchemingDatasetsPlugin,
    SchemingGroupsPlugin, SchemingOrganizationsPlugin)
from ckanext.scheming.workers import worker_pool
from ckanext.scheming.stats import completion_stats

from ckanapi import LocalCKAN, NotFound, ValidationError, SearchIndexError

import sys
import json
from datetime import datetime
from contextlib import contextmanager

def _get_schemas():
    """
    Find the scheming plugins and return (dataset_schemas, group_schemas,
        organization_schemas)

    If any plugin is not loaded, return None instead of schema dicts
    for that value.
    """
    schema_types = []
    for s in (SchemingDatasetsPlugin, SchemingGroupsPlugin,
            SchemingOrganizationsPlugin):
        if s.instance is None:
            schema_types.append(None)
            continue
        schema_types.append(s.instance._schemas)
    return schema_types


class SchemingCommand(CkanCommand):
    """
    ckanext-scheming schema management commands

    Usage::

        paster scheming show
                        load-datasets <.jsonl file>
                        load-groups <.jsonl file>
                        load-organizations <.jsonl file>

    Options::

        -u/--ckan-user <username>   sets the owner of objects created,
                                    default: ckan system user
        -s/--start-record <n>       start loading from record, default: 1
        -m/--max-records <m>        maximum records to load,
                                    default: unlimited
        --create-only               don't update existing records
        -p/--processes <num>        sets the number of worker processes,
                                    default: 1
        -l/--log <filename>         write log of actions to filename
        -z/--gzip                   read/write gzipped data


    """
    summary = __doc__.split('\n')[0]
    usage = __doc__

    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option('-c', '--config', dest='config',
        default='development.ini', help='Config file to use.')
    parser.add_option('-u', '--ckan-user', dest='ckan_user',
        default=None)
    parser.add_option('-s', '--start-record', dest='start_record',
        default=1, type="int")
    parser.add_option('-m', '--max-records', dest='max_records',
        default=-1, type="int")
    parser.add_option('-p', '--processes', dest='processes',
        default=1, type="int")
    parser.add_option('-l', '--log', dest='log', default=None)
    parser.add_option('-z', '--gzip', dest='gzip', action='store_true')
    parser.add_option('--create-only', dest='create_only', action='store_true')


    def command(self):
        cmd = self.args[0]
        self._load_config()

        if cmd == 'show':
            self._show()
        elif cmd in ('load-datasets', 'load-groups', 'load-organizations'
                ) and len(self.args) == 2:
            thing = cmd[5:-1] # 'dataset', 'group' or 'organization'
            self._load_things(thing, self.args[1])
        elif cmd in ('load-dataset-worker', 'load-group-worker',
                'load-organization-worker'):
            thing = cmd[5:-7] # 'dataset', 'group' or 'organization'
            self._load_things_worker(thing)
        else:
            print self.__doc__

    def _show(self):
        for s, n in zip(_get_schemas(), ("Dataset", "Group", "Organization")):
            print n, "schemas:"
            if s is None:
                print "    plugin not loaded\n"
                continue
            if not s:
                print "    no schemas"
            for typ in sorted(s):
                print " * " + json.dumps(typ)
                for field in s[typ]['fields']:
                    print "   - " + json.dumps(field['field_name'])
            print

    def _load_things(self, thing, jsonl):
        thing_number = ['dataset', 'group', 'organization'].index(thing)
        log = None
        if self.options.log:
            log = open(self.options.log, 'a')

        def line_reader():
            """
            generate stripped records from jsonl
            handles start_record, max_records and gzip options
            """
            start_record = self.options.start_record
            max_records = self.options.max_records
            if self.options.gzip:
                source_file = GzipFile(jsonl)
            else:
                source_file = open(jsonl)
            for num, line in enumerate(source_file, 1):
                if num < start_record:
                    continue
                if max_records >= 0 and num >= start_record + max_records:
                    break
                yield num, line.strip()

        cmd = [
            sys.argv[0],
            'scheming',
            'load-%s-worker' % thing,
            '-c', self.options.config,
            ]
        if self.options.ckan_user:
            cmd += ['-u', self.options.ckan_user]
        if self.options.create_only:
            cmd += ['--create-only']

        stats = completion_stats(self.options.processes)
        pool = worker_pool(cmd, self.options.processes, line_reader())
        with _quiet_int_pipe():
            for job_ids, finished, result in pool:
                timestamp, action, error, response = json.loads(result)
                print finished, job_ids, stats.next(), action,
                print json.dumps(response) if response else ''
                if log:
                    log.write(json.dumps([
                        timestamp,
                        finished,
                        action,
                        error,
                        response,
                        ]) + '\n')
                    log.flush()

    def _load_things_worker(self, thing):
        """
        a process that accepts lines of json on stdin which is parsed and
        passed to the {thing}_create/update actions.  it produces lines of json
        which are the responses from each action call.
        """
        supported_things = ('dataset', 'group', 'organization')
        assert thing in supported_things, thing
        thing_number = supported_things.index(thing)

        localckan = LocalCKAN(self.options.ckan_user, {'return_id_only':True})
        a = localckan.action
        thing_show, thing_create, thing_update = [
            (a.package_show, a.package_create, a.package_update),
            (a.group_show, a.group_create, a.group_update),
            (a.organization_show, a.organization_create, a.organization_update),
            ][thing_number]

        def reply(action, error, response):
            """
            format messages to be sent back to parent process
            """
            sys.stdout.write(json.dumps([
                datetime.now().isoformat(),
                action,
                error,
                response]) + '\n')

        for line in iter(sys.stdin.readline, ''):
            try:
                obj = json.loads(line.decode('utf-8'))
            except UnicodeDecodeError, e:
                obj = None
                reply('read', 'UnicodeDecodeError', unicode(e))

            if obj:
                existing = None
                if not self.options.create_only:
                    # use either id or name to locate existing records
                    name = obj.get('id')
                    if name:
                        try:
                            existing = thing_show(id=name)
                        except NotFound:
                            pass
                    name = obj.get('name')
                    if not existing and name:
                        try:
                            existing = thing_show(id=name)
                            # matching id required for *_update
                            obj['id'] = existing['id']
                        except NotFound:
                            pass
                    # FIXME: compare and reply when 'unchanged'?

                act = 'update' if existing else 'create'
                try:
                    r = (thing_update if existing else thing_create)(**obj)
                except ValidationError, e:
                    reply(act, 'ValidationError', e.error_dict)
                except SearchIndexError, e:
                    reply(act, 'SearchIndexError', unicode(e))
                else:
                    reply(act, None, r['name'])
            sys.stdout.flush()

@contextmanager
def _quiet_int_pipe():
    """
    let pipe errors and KeyboardIterrupt exceptions cause silent exit
    """
    try:
        yield
    except KeyboardInterrupt:
        pass
    except IOError, e:
        if e.errno != 32:
            raise
