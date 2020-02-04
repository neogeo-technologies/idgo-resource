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

from pathlib import Path
from zipfile import ZipFile
import json
import os.path
import shutil
from functools import reduce
from operator import iconcat

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django import forms

from idgo_admin.utils import readable_file_size
from idgo_resource.forms import ModelResourceForm
from idgo_resource import logger
from idgo_resource.models import ResourceFormats
from idgo_resource.models import Store
from idgo_resource.redis_client import Handler as RedisHandler


DOWNLOAD_SIZE_LIMIT = getattr(settings, 'RESOURCE_STORE_DOWNLOAD_SIZE_LIMIT', 104857600)  # Default:100Mio
EXTENSIONS = getattr(settings, 'RESOURCE_STORE_EXTENSIONS', ['zip', 'rar', '7z', 'tar', 'tar.gz'])
DIRECTORY_STORAGE = settings.DIRECTORY_STORAGE


def file_size(value):
    size_limit = DOWNLOAD_SIZE_LIMIT
    if value.size > size_limit:
        message = (
            'Le fichier {name} ({size}) dépasse la '
            'limite de taille autorisée : {max_size}.'
        ).format(
            name=value.name,
            size=readable_file_size(value.size),
            max_size=readable_file_size(size_limit)
        )
        raise ValidationError(message)


try:
    mimetype = []
    for item in ResourceFormats.objects.filter(extension__in=EXTENSIONS):
        if item.mimetype:
            mimetype.append(item.mimetype)
except Exception:
    ACCEPT_RESOURCE_FORMATS = []
else:
    ACCEPT_RESOURCE_FORMATS = list(set(reduce(iconcat, mimetype, [])))


class ModelResourceStoreForm(forms.ModelForm):

    class Meta:
        model = Store
        fields = (
            'file_path',
        )

    class CustomClearableFileInput(forms.ClearableFileInput):
        template_name = 'idgo_admin/widgets/file_drop_zone.html'

    file_path = forms.FileField(
        label="",  # Vide
        required=True,
        validators=[file_size],
        widget=CustomClearableFileInput(
            attrs={
                'value': '',  # IMPORTANT
                'max_size_info': DOWNLOAD_SIZE_LIMIT,
                'accept': ', '.join(ACCEPT_RESOURCE_FORMATS),
            },
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_file_path(self):
        # We check if a file has been uploaded
        data = self.data.get('file_path')
        if data == '':
            raise forms.ValidationError('Ce champs ne peut être vide.')
        # We send the verified file
        return self.cleaned_data['file_path']

    def clean(self):
        # TODO: Vérifier si le type de fichier est autorisé
        # TODO: Vérifier le contenu ??? (à voir plus tard)
        return self.cleaned_data


class EmitResourceStoreForm(ModelResourceStoreForm):
    pass


class UpdateResourceStoreForm(ModelResourceStoreForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file_path'].widget.attrs['value'] = ''
        # self.fields['file_path'].initial = ''
        # self.fields['file_path'].widget.attrs['value'] = self.instance.get_file_url


class BaseResourceStoreForm(ModelResourceForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['format_type'].queryset = \
            ResourceFormats.objects.filter(extension__in=EXTENSIONS).order_by('extension')

    def clean(self):
        redis_key = self.cleaned_data.get('redis_key')
        if redis_key:
            data = json.loads(RedisHandler().retreive(redis_key))
            self.filename = data['filename']  # `filename` DOIT exister.
            file_size = data['size']

            if not os.path.exists(self.filename) and \
               not os.path.isfile(self.filename) and \
               not os.path.getsize(self.filename) == file_size:
                raise ValidationError(
                    (
                        'Le fichier {name} semble perdu dans des profondeurs insondables.'
                    ).format(name=data['name'])
                )

        return self.cleaned_data

    def get_dataset(self, data):
        try:
            Dataset = apps.get_model(app_label='idgo_admin', model_name='Dataset')
            dataset = Dataset.objects.get(pk=data.get('dataset'))
        except Dataset.DoesNotExist():
            logger.error(
                'Dataset not found: model Datatset - pk {}'.format(
                    data.get('dataset'))
            )
            pass
        else:
            return dataset

    def store_dir(self, data, flush=False):
        if data.get('content_type') == 'application/zip':
            with ZipFile(data.get('filename'), 'r') as zip_obj:
                # Extract all the contents of zip file in different directory
                store_path = '{}/{}'.format(DIRECTORY_STORAGE, self.instance.pk)
                if flush and Path(store_path).exists():
                    shutil.rmtree(store_path)
                Path(store_path).mkdir(parents=True, exist_ok=True)
                zip_obj.extractall(store_path)

        # TODO: RAR, TAR, etc.

    def set_file(self, data):
        try:
            RelatedModel = apps.get_model(
                app_label='idgo_resource', model_name=data.get('related_model'))
            instance = RelatedModel.objects.get(pk=data.get('related_pk'))
            instance.resource = self.instance
        except RelatedModel.DoesNotExist:
            logger.error(
                'Resource File not found: model {} - pk {}'.format(
                    data.get('related_model'), data.get('related_pk'))
            )
            pass
        else:
            instance.save()

    def save(self, commit=True, *args, **kwargs):
        resource = self.instance
        dataset = kwargs.pop('dataset', None)
        if dataset:
            resource.dataset = dataset

        # Keep  this 'save' above all the others related instances handlers
        resource.save()
        redis_key = self.cleaned_data.get('redis_key')
        if redis_key:
            data = json.loads(RedisHandler().retreive(redis_key))
            # Related instances handlers:
            self.set_file(data)
            self.store_dir(data, flush=True)
        return resource


class CreateResourceStoreForm(BaseResourceStoreForm):
    """Formulaire de création d'une ressource de type Store."""


class EditResourceStoreForm(BaseResourceStoreForm):
    """Formulaire d'édition d'une ressource de type Store."""
