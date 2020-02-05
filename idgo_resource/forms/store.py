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


DIRECTORY_STORAGE = settings.DIRECTORY_STORAGE

DOWNLOAD_SIZE_LIMIT = getattr(settings, 'RESOURCE_STORE_DOWNLOAD_SIZE_LIMIT', 104857600)  # Default:100Mio
EXTENSIONS = getattr(settings, 'RESOURCE_STORE_EXTENSIONS', ['zip'])
try:
    filter = {'extension__in': EXTENSIONS, 'is_gis_format': False}
    RESOURCE_FORMATS = ResourceFormats.objects.filter(**filter).order_by('extension')
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
        required=False,
        validators=[file_size],
        widget=CustomClearableFileInput(
            attrs={
                'value': '',
                'max_size_info': DOWNLOAD_SIZE_LIMIT,
                # accept
            },
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extensions = EXTENSIONS
        self.mimetypes = list(set(reduce(iconcat, [item.mimetype for item in RESOURCE_FORMATS], [])))
        self.fields['file_path'].widget.attrs['accept'] = ', '.join(self.mimetypes)

    def clean_file_path(self):
        # We check if a file has been uploaded
        file_path = self.cleaned_data.get('file_path')
        if not file_path:
            raise forms.ValidationError("Ce champs ne peut être vide.")
        if file_path.content_type not in self.mimetypes:
            raise forms.ValidationError("Le type MIME du fichier n'est pas autorisé.")
        # We send the verified file
        return file_path


class EmitResourceStoreForm(ModelResourceStoreForm):
    pass


class UpdateResourceStoreForm(ModelResourceStoreForm):

    def __init__(self, *args, **kwargs):
        kwargs['instance'].file_path = None
        super().__init__(*args, **kwargs)


class BaseResourceStoreForm(ModelResourceForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['format_type'].queryset = RESOURCE_FORMATS

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
                        "Le fichier {name} semble perdu dans des profondeurs insondables."
                    ).format(name=data['name'])
                )

        return self.cleaned_data

    def get_dataset(self, data):
        try:
            Dataset = apps.get_model(app_label='idgo_admin', model_name='Dataset')
            dataset = Dataset.objects.get(pk=data.get('dataset'))
        except Dataset.DoesNotExist():
            logger.error(
                "Dataset not found: model Datatset - pk {}".format(data.get('dataset'))
            )
        else:
            return dataset

    def _unzip(self, filename, flush=False):
        with ZipFile(filename, 'r') as zip_obj:
            store_path = os.path.join(DIRECTORY_STORAGE, str(self.instance.pk))
            if flush and Path(store_path).exists():
                shutil.rmtree(store_path)
            Path(store_path).mkdir(parents=True, exist_ok=True)
            zip_obj.extractall(store_path)

    def store_directory(self, data, flush=False):

        extensions = dict(
            (item.extension, item.mimetype)
            for item in self.fields['format_type'].queryset
        )

        for extension, mimetypes in extensions.items():
            if data.get('content_type') in mimetypes:
                if extension == 'zip':
                    self._unzip(data.get('filename'), flush=flush)
                else:
                    # TODO
                    raise NotImplementedError

    def set_file(self, data):
        try:
            RelatedModel = apps.get_model(
                app_label='idgo_resource', model_name=data.get('related_model'))
            instance = RelatedModel.objects.get(pk=data.get('related_pk'))
            instance.resource = self.instance
        except RelatedModel.DoesNotExist:
            logger.error(
                "Resource File not found: model {} - pk {}".format(
                    data.get('related_model'), data.get('related_pk')
                )
            )
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
            self.store_directory(data, flush=True)
        return resource


class CreateResourceStoreForm(BaseResourceStoreForm):
    """Formulaire de création d'une ressource de type Store."""


class EditResourceStoreForm(BaseResourceStoreForm):
    """Formulaire d'édition d'une ressource de type Store."""
