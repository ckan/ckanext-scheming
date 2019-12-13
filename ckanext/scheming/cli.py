# -*- coding: utf-8 -*-

from __future__ import print_function

import click

import ckanext.scheming.utils as utils


@click.group(short_help=u"ckanext-scheming commands")
def scheming():
    pass


@scheming.command()
@click.pass_context
def show(ctx):
    flask_app = ctx.obj.app.apps[u'flask_app']._wsgi_app
    with flask_app.test_request_context():
        click.echo(utils.describe_schemas())
