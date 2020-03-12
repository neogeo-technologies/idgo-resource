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


import json
import os.path
from functools import reduce
from operator import iconcat

from django.conf import settings
from django.core.exceptions import ValidationError
from django import forms

from idgo_admin.ckan_module import CkanHandler
from idgo_admin.ckan_module import CkanUserHandler
from idgo_admin.utils import readable_file_size
from idgo_resource.forms import ModelResourceForm
from idgo_resource import logger
from idgo_resource.models import ResourceFormats
from idgo_resource.models import Upload
from idgo_resource.redis_client import Handler as RedisHandler


DOWNLOAD_SIZE_LIMIT = getattr(settings, 'RESOURCE_STORE_DOWNLOAD_SIZE_LIMIT', 104857600)  # Default:100Mio
try:
    RESOURCE_FORMATS = ResourceFormats.objects.all().order_by('extension')
except:
    RESOURCE_FORMATS = []


def file_size(value):
    size_limit = DOWNLOAD_SIZE_LIMIT
    if value.size > size_limit:
        message = (
            "Le fichier {name} ({size}) dépasse la limite de taille autorisée : {max_size}."
        ).format(
            name=value.name, size=readable_file_size(value.size), max_size=readable_file_size(size_limit))
        raise ValidationError(message)


class ResourceUploadForm(forms.Form):

    class CustomClearableFileInput(forms.ClearableFileInput):
        template_name = 'idgo_admin/widgets/file_drop_zone.html'

    file_path = forms.FileField(
        label="",  # Vide
        required=False,
        validators=[file_size],
        widget=CustomClearableFileInput(
            attrs={
                'value': '',
                'max_size_info': DOWNLOAD_SIZE_LIMIT,
                # accept => set in __init__()
            },
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extensions = list(set([item.extension for item in RESOURCE_FORMATS if item.extension]))
        self.mimetypes = list(set(reduce(iconcat, [item.mimetype for item in RESOURCE_FORMATS if item.mimetype], [])))
        self.fields['file_path'].widget.attrs['accept'] = ', '.join(self.mimetypes)

    def clean_file_path(self):
        file_path = self.cleaned_data.get('file_path')
        if not file_path:
            raise forms.ValidationError("Ce champs ne peut être vide.")
        if file_path.content_type not in self.mimetypes:
            raise forms.ValidationError("Le type MIME du fichier n'est pas autorisé.")
        return file_path


class ModelResourceUploadForm(ResourceUploadForm, forms.ModelForm):

    class Meta:
        model = Upload
        fields = (
            'file_path',
        )


class EmitResourceUploadForm(ModelResourceUploadForm):
    pass


class UpdateResourceUploadForm(ModelResourceUploadForm):

    def __init__(self, *args, **kwargs):
        kwargs['instance'].file_path = None
        super().__init__(*args, **kwargs)


class BaseResourceUploadForm(ModelResourceForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['format_type'].queryset = RESOURCE_FORMATS

    def clean(self):
        redis_key = self.cleaned_data.get('redis_key')
        if redis_key:
            data = RedisHandler().retreive(redis_key)
            self.filename = data['filename']  # `filename` MUST exist.
            file_size = data['size']

            if not os.path.exists(self.filename) and \
               not os.path.isfile(self.filename) and \
               not os.path.getsize(self.filename) == file_size:
                raise ValidationError(
                    (
                        "Le fichier {name} semble perdu dans des profondeurs insondables."
                    ).format(name=data['name'])
                )

        return self.cleaned_data

    def save_ckan_resource(self, with_user=None):
        resource = self.instance

        if with_user:
            username = with_user.username
        else:
            username = resource.dataset.editor.username

        upload = open(self.filename, 'rb')

        data = {
            'id': str(resource.ckan_id),
            'url': '',
            'name': resource.title,
            'description': resource.description,
            'lang': resource.language,
            'data_type': resource.resource_type,
            'upload': upload,
            'size': resource.upload.file_path.size,
            'format': resource.format_type.ckan_format,
            'mimetype': resource.format_type.mimetype[0],
            'view_type': resource.format_type.ckan_view,
            #
            'api': '{}',
            'restricted_by_jurisdiction': 'False',
            'extracting_service': 'False',
            'crs': '',
            'restricted': json.dumps({'level': 'public'}),
        }

        ckan_package = CkanHandler.get_package(str(resource.dataset.ckan_id))
        apikey = CkanHandler.get_user(username)['apikey']
        with CkanUserHandler(apikey=apikey) as ckan:
            ckan.publish_resource(ckan_package, **data)

        upload.close()


class CreateResourceUploadForm(BaseResourceUploadForm):
    """Formulaire de création d'une ressource de type Upload."""


class EditResourceUploadForm(BaseResourceUploadForm):
    """Formulaire d'édition d'une ressource de type Upload."""
