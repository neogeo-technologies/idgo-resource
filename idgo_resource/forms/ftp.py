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


import os.path
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django import forms

from idgo_admin.utils import readable_file_size
from idgo_resource.forms import ModelResourceForm
from idgo_resource.models import ResourceFormats
from idgo_resource.models import Ftp
from idgo_resource.redis_client import Handler as RedisHandler


DOWNLOAD_SIZE_LIMIT = getattr(settings, 'RESOURCE_STORE_DOWNLOAD_SIZE_LIMIT', 104857600)  # Default:100Mio
try:
    RESOURCE_FORMATS = ResourceFormats.objects.all().order_by('extension')
except:
    RESOURCE_FORMATS = []

FTP_DIR = settings.FTP_DIR
try:
    FTP_UPLOADS_DIR = settings.FTP_UPLOADS_DIR
except AttributeError:
    FTP_UPLOADS_DIR = 'uploads'

try:
    FTP_USER_PREFIX = settings.FTP_USER_PREFIX
except AttributeError:
    FTP_USER_PREFIX = ''


def file_size(value):
    size_limit = DOWNLOAD_SIZE_LIMIT
    if value.size > size_limit:
        message = (
            "Le fichier {name} ({size}) dépasse la limite de taille autorisée : {max_size}."
        ).format(
            name=value.name, size=readable_file_size(value.size), max_size=readable_file_size(size_limit))
        raise ValidationError(message)


class ResourceFtpForm(forms.Form):

    file_path = forms.ChoiceField(
        label="Les fichiers que vous avez déposés sur votre compte FTP apparaîssent dans la liste ci-dessous :",
        required=False,
        choices=[],
    )

    def __init__(self, *args, user=None, **kwargs):
        kwargs.setdefault('resource_formats', RESOURCE_FORMATS)
        resource_formats = kwargs.pop('resource_formats')
        super().__init__(*args, **kwargs)

        self.extensions = list(set([item.extension for item in resource_formats if item.extension]))

        sub_dir = '{prefix}{username}'.format(
            prefix=FTP_USER_PREFIX, username=user.username)
        dir = os.path.join(FTP_DIR, sub_dir, FTP_UPLOADS_DIR)

        choices = [(None, 'Veuillez sélectionner un fichier')]
        for path, subdirs, files in os.walk(dir):
            for name in files:
                file_path = Path(os.path.join(path, name))
                if file_path.suffix[1:] not in self.extensions:
                    continue
                if str(file_path).startswith(FTP_DIR):
                    filename = str(file_path)[len(FTP_DIR):]
                else:
                    filename = str(file_path)
                choices.append((str(file_path), 'file://{}'.format(filename)))
        self.fields['file_path'].choices = choices

    def clean_file_path(self):
        file_path = self.cleaned_data.get('file_path')
        if not file_path:
            raise forms.ValidationError("Ce champs ne peut être vide.")
        p = Path(file_path)
        if not p.exists():
            raise forms.ValidationError("Le fichier n'existe pas.")
        if p.is_dir():
            raise forms.ValidationError("Les répertoires ne sont pas supportés par l'application.")
        return file_path


class ModelResourceFtpForm(ResourceFtpForm, forms.ModelForm):

    class Meta:
        model = Ftp
        fields = (
            'file_path',
        )


class EmitResourceFtpForm(ModelResourceFtpForm):
    pass


class UpdateResourceFtpForm(ModelResourceFtpForm):

    def __init__(self, *args, **kwargs):
        kwargs['instance'].file_path = None
        super().__init__(*args, **kwargs)


class BaseResourceFtpForm(ModelResourceForm):

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


class CreateResourceFtpForm(BaseResourceFtpForm):
    """Formulaire de création d'une ressource de type Ftp."""


class EditResourceFtpForm(BaseResourceFtpForm):
    """Formulaire d'édition d'une ressource de type Ftp."""
