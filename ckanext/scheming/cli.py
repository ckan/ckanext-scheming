# -*- coding: utf-8 -*-

import click

from ckan.cli import error_shout, click_config_option
from ckan.cli.cli import CkanCommand
import ckanext.scheming.utils as utils

@click.group(short_help=u"ckanext-scheming commands")
@click.help_option(u"-h", u"--help")
@click_config_option
@click.pass_context
def scheming(ctx, config, *args, **kwargs):
    ctx.obj = CkanCommand(config)


@scheming.command()
@click.pass_context
def show(ctx):
    flask_app = ctx.obj.app.apps[u'flask_app']._wsgi_app
    with flask_app.test_request_context():
        print(utils.describe_schemas())
