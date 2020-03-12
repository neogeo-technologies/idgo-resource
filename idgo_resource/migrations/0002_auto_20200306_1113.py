# -*- coding: utf-8 -*-
# Generated by Django 1.11.25 on 2020-03-06 10:13
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('idgo_resource', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='store',
            name='resource',
        ),
        migrations.DeleteModel(
            name='Store',
        ),
        migrations.AlterModelTable(
            name='download',
            table='idgo_resource_download',
        ),
        migrations.AlterModelTable(
            name='ftp',
            table='idgo_resource_ftp',
        ),
        migrations.AlterModelTable(
            name='href',
            table='idgo_resource_href',
        ),
        migrations.AlterModelTable(
            name='upload',
            table='idgo_resource_upload',
        ),
    ]