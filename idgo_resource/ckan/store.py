# Copyright (c) 2017-2020 Neogeo-Technologies.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import io
import json
import os.path
from functools import reduce
import magic
from mimetypes import MimeTypes
import os
import pathlib
from urllib.parse import urljoin

from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse

from idgo_admin.ckan_module import CkanHandler
from idgo_admin.ckan_module import CkanUserHandler


DIRECTORY_STORAGE = settings.DIRECTORY_STORAGE
DOMAIN = settings.DOMAIN_NAME

Mime = magic.Magic(mime=True)


def iterate(location, base_url=None):
    files = []
    for filename in pathlib.Path(location).glob('**/[!_\.]*'):
        if not filename.is_dir():
            href = reduce(
                urljoin, [DOMAIN, base_url, str(filename.relative_to(location))])
            content_type = MimeTypes().guess_type(str(filename))[0] \
                or Mime.from_file(str(filename))
            size = filename.stat().st_size

            files.append({
                'content_type': content_type,
                'href': href,
                'size': size,
            })
    return files


def synchronize(instance, with_user=None):

    ckan_package = CkanHandler.get_package(str(instance.dataset.ckan_id))
    username = with_user and with_user.username or instance.dataset.editor.username
    apikey = CkanHandler.get_user(username)['apikey']

    location = os.path.join(DIRECTORY_STORAGE, str(instance.pk))

    base_url = reverse('resource:directory_storage', kwargs={
        'dataset_id': instance.dataset.pk,
        'resource_id': instance.pk
    })

    files = iterate(location, base_url=base_url)
    html = render_to_string(
        'resource/store/ckan_resource_template.html', context={'files': files})
    upload = io.BytesIO(html.encode('utf-8'))

    data = {
        'id': str(instance.ckan_id),
        'url': instance.store.url,
        'name': instance.title,
        'description': instance.description,
        'lang': instance.language,
        'data_type': instance.resource_type,
        'view_type': 'text_view',
        'upload': upload,
        'size': '',
        'mimetype': 'text/html',
        'format': '',
        'api': '{}',
        'restricted_by_jurisdiction': '',
        'extracting_service': 'False',
        'crs': '',
        'restricted': json.dumps({'level': 'public'}),
    }

    with CkanUserHandler(apikey=apikey) as ckan:
        ckan.publish_resource(ckan_package, **data)
