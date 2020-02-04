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
from functools import reduce
import magic
from mimetypes import MimeTypes
from operator import ior
import os
import os.path
import pathlib
from urllib.parse import urljoin

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse  # from django.urls import reverse

from idgo_admin.ckan_module import CkanHandler
from idgo_admin.ckan_module import CkanUserHandler
from idgo_admin.models import Dataset
from idgo_admin.shortcuts import get_object_or_404_extended
from idgo_admin.shortcuts import render_with_info_profile
from idgo_admin.shortcuts import user_and_profile
from idgo_resource.forms import CreateResourceStoreForm
from idgo_resource.forms import EditResourceStoreForm
from idgo_resource.forms import EmitResourceStoreForm
from idgo_resource.forms import UpdateResourceStoreForm
from idgo_resource.models import ResourceFormats
from idgo_resource.models import Resource
from idgo_resource.redis_client import Handler as RedisHandler


CKAN_URL = settings.CKAN_URL
DIRECTORY_STORAGE = settings.DIRECTORY_STORAGE
DOMAIN = settings.DOMAIN_NAME
LOGIN_URL = settings.LOGIN_URL

mime = magic.Magic(mime=True)

decorators = [csrf_exempt, login_required(login_url=LOGIN_URL)]


@method_decorator(decorators, name='dispatch')
class ResourceStoreBaseView(View):

    def get(self, *args, **kwargs):
        raise NotImplementedError

    def post(self, *args, **kwargs):
        raise NotImplementedError

    def redis_create_key(self, user, instance_store, instance_store_pk, content_type):
        return RedisHandler().create(
            user=user.pk,
            content_type=content_type,
            name=instance_store.file_path.name,
            size=instance_store.file_path.size,
            filename=instance_store.file_path.path,
            related_pk=instance_store_pk,
            related_model=type(instance_store).__name__
        )

    def init_resource_form(self, instance_store, title, content_type, redis_key, resource=None):

        filters = [
            Q(mimetype__overlap=[content_type]),
            Q(extension=instance_store.file_path.name.split('.')[-1])
        ]
        format_type = ResourceFormats.objects.filter(reduce(ior, filters)).distinct().first()

        resource_form = CreateResourceStoreForm(
            # instance=resource,  # Si on veut recuperer les anciennes valeurs
            initial={
                'title': title,
                'language': 'french',
                'resource_type': 'annexe',
                'format_type': format_type,
                'redis_key': redis_key,
                'description': resource.description if resource else ''
            }
        )
        return resource_form


class EmitResourceStore(ResourceStoreBaseView):
    """Emettre un fichier pour la création d'une ressource de type Store."""

    def get(self, request, dataset_id=None, *args, **kwargs):
        user, profile = user_and_profile(request)
        dataset = get_object_or_404_extended(Dataset, user, include={'id': dataset_id})
        context = {
            'form': EmitResourceStoreForm(),
            'dataset': dataset,
        }
        return render_with_info_profile(request, 'resource/store/create.html', context)

    @transaction.atomic
    def post(self, request, dataset_id=None, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404_extended(Dataset, user, include={'id': dataset_id})
        form = EmitResourceStoreForm(data=request.POST, files=request.FILES)

        if not form.is_valid():
            context = {
                'form': EmitResourceStoreForm(),
                'dataset': dataset
            }
            return render_with_info_profile(request, 'resource/store/create.html', context)

        instance_store = form.save()

        content_type = request.FILES.get('file_path').content_type
        title = request.FILES.get('file_path').name

        # Création d'une entrée REDIS pour suivre la vie de la création de la ressource
        redis_key = self.redis_create_key(user, instance_store, instance_store.pk, content_type)

        resource_form = self.init_resource_form(instance_store, title, content_type, redis_key)

        context = {
            'form': resource_form,
            'dataset': dataset,
        }
        return render_with_info_profile(request, 'resource/create.html', context)


class UpdateResourceStore(ResourceStoreBaseView):
    """Emettre un nouveau fichier pour une ressource de type Store."""

    def get(self, request, dataset_id, resource_id, *args, **kwargs):

        user, profile = user_and_profile(request)

        dataset = get_object_or_404_extended(Dataset, user, include={'id': dataset_id})
        resource = get_object_or_404_extended(Resource, user, include={'id': resource_id})

        store = resource.store if hasattr(resource, 'store') else None
        context = {
            'form': UpdateResourceStoreForm(instance=store),
            'dataset': dataset,
            'resource': resource,
            'store': store
        }
        return render_with_info_profile(request, 'resource/store/update.html', context)

    @transaction.atomic
    def post(self, request, dataset_id, resource_id, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404_extended(Dataset, user, include={'id': dataset_id})
        resource = get_object_or_404_extended(Resource, user, include={'id': resource_id})

        old_store = resource.store
        # store = resource.store if hasattr(resource, 'store') else None
        form = UpdateResourceStoreForm(data=request.POST, files=request.FILES, instance=old_store)

        if not form.is_valid():
            context = {
                'form': EmitResourceStoreForm(),
                'dataset': dataset,
                'resource': resource,
                'store': old_store,
            }
            return render_with_info_profile(request, 'resource/store/update.html', context)

        # else:
        updated_store = form.save()

        content_type = request.FILES.get('file_path').content_type
        title = request.FILES.get('file_path').name

        # Création d'une entrée REDIS pour suivre la vie de la création de la ressource
        redis_key = self.redis_create_key(user, updated_store, updated_store.pk, content_type)

        resource_form = self.init_resource_form(updated_store, title, content_type, redis_key, resource)

        context = {
            'form': resource_form,
            'dataset': dataset,
            'resource': resource,
            'store': updated_store
        }
        return render_with_info_profile(request, 'resource/edit.html', context)


@method_decorator(decorators, name='dispatch')
class CreateResourceStore(View):
    """Créer une ressource de type Store."""

    @transaction.atomic
    def post(self, request, dataset_id=None, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404(Dataset, pk=dataset_id)
        form = CreateResourceStoreForm(data=request.POST)
        context = {
            'form': form,
            'dataset': dataset,
        }

        if not form.is_valid():
            return render_with_info_profile(request, 'resource/create_store.html', context)
        resource = form.save(dataset=dataset)

        save_ckan_resource(resource, with_user=user)

        msg = (
            'La ressource a été créée avec succès. '
            'Souhaitez-vous <a href="{0}">ajouter une nouvelle ressource</a> '
            'ou bien <a href="{1}" target="_blank">voir la ressource dans CKAN</a> ?'
        ).format(
            reverse('idgo_admin:resource', kwargs={'dataset_id': dataset.pk}),
            resource.ckan_url,
        )
        messages.success(request, msg)

        url_params = {
            'dataset_id': dataset_id,
            'resource_id': resource.pk
        }
        url = reverse('idgo_resource:show_resource_store', kwargs=url_params)
        return HttpResponseRedirect(url)


@method_decorator(decorators, name='dispatch')
class EditResourceStore(View):
    """Editer d'une resource de type Store."""

    EditForm = EditResourceStoreForm

    def get(self, request, dataset_id, resource_id, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404(Dataset, pk=dataset_id)
        resource = get_object_or_404(Resource, pk=resource_id)
        form = self.EditForm(instance=resource)

        context = {'form': form, 'dataset': dataset, 'resource': resource}
        return render_with_info_profile(request, 'resource/edit.html', context)

    @transaction.atomic
    def post(self, request, dataset_id, resource_id, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404_extended(Dataset, user, include={'id': dataset_id})
        resource = get_object_or_404_extended(Resource, user, include={'id': resource_id})
        form = self.EditForm(data=request.POST, instance=resource)

        if not form.is_valid():
            context = {'form': form, 'dataset': dataset, 'resource': resource}
            return render_with_info_profile(request, 'resource/edit.html', context)

        resource = form.save(dataset=dataset)
        save_ckan_resource(resource, with_user=user)

        msg = (
            'La ressource a été mise à jour avec succès. '
            'Souhaitez-vous <a href="{0}">ajouter une nouvelle ressource</a> '
            'ou bien <a href="{1}" target="_blank">voir la ressource dans CKAN</a> ?'
        ).format(
            reverse('idgo_admin:resource', kwargs={'dataset_id': dataset.pk}),
            resource.ckan_url,
        )
        messages.success(request, msg)

        kwargs = {'dataset_id': dataset_id, 'resource_id': resource.pk}
        url = reverse('idgo_resource:show_resource_store', kwargs=kwargs)
        return HttpResponseRedirect(url)


@method_decorator(decorators, name='dispatch')
class ShowResourceStore(View):
    """Voir une ressource de type Store."""

    def get(self, request, dataset_id, resource_id, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404_extended(Dataset, user, include={'id': dataset_id})
        resource = get_object_or_404_extended(Resource, user, include={'id': resource_id})

        location = os.path.join(DIRECTORY_STORAGE, str(resource.pk))

        # TODO: Paginer?
        files = []
        for filename in pathlib.Path(location).glob('**/[!_\.]*'):
            if not filename.is_dir():

                path = str(filename.relative_to(location))

                mime = magic.Magic(mime=True)
                content_type = MimeTypes().guess_type(str(filename))[0] \
                    or mime.from_file(str(filename))
                size = filename.stat().st_size

                file = {
                    'path': path,
                    'content_type': content_type,
                    'size': size
                }
                files.append(file)

        context = {'dataset': dataset, 'resource': resource, 'files': files}
        return render_with_info_profile(request, 'resource/store/show.html', context)


@method_decorator(decorators, name='dispatch')
class DeleteResourceStore(View):
    """Supprimer une ressource de type Store."""

    @transaction.atomic
    def get(self, request, dataset_id, resource_id, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404(Dataset, pk=dataset_id)
        resource = get_object_or_404(Resource, pk=resource_id)

        store = resource.store if hasattr(resource, 'store') else None
        if store:
            resource.store.delete()
        resource.delete()

        kwargs = {'dataset_id': dataset.id}
        url = reverse('idgo_resource:go_for_resource', kwargs=kwargs)
        return HttpResponseRedirect(url)


# =====================
# DIRECTORY STORAGE API
# =====================


class ShowDirectory:
    def __init__(self, *args, **kwargs):
        self.location = None

    def iter_files(self, filename=None):
        for filename in pathlib.Path(self.location).glob(filename or '**/[!_\.]*'):
            yield filename

    def get_file(self, filename):
        try:
            return next(self.iter_files(filename=filename))
        except (StopIteration, SystemError):
            raise KeyError(filename)

    def has_file(self, filename):
        try:
            self.get_file(filename)
        except KeyError:
            return False
        return True


@method_decorator([csrf_exempt], name='dispatch')
class ShowDirectoryStorage(ShowDirectory, View):

    def get(self, request, dataset_id=None, resource_id=None, *args, **kwargs):

        dataset = get_object_or_404(Dataset, id=dataset_id)
        resource = get_object_or_404(Resource, id=resource_id)

        self.location = os.path.join(DIRECTORY_STORAGE, str(resource.pk))
        base_url = request.build_absolute_uri()

        data = []
        for filename in self.iter_files():
            if not filename.is_dir():
                path = str(filename.relative_to(self.location))
                url = urljoin(base_url, path)

                mime = magic.Magic(mime=True)
                content_type = MimeTypes().guess_type(str(filename))[0] \
                    or mime.from_file(str(filename))
                size = filename.stat().st_size

                data.append({
                    'url': url,
                    'content-type': content_type,
                    'size': size
                })

        return JsonResponse(data, safe=False)


@method_decorator([csrf_exempt], name='dispatch')
class ShowDirectoryStorageGlob(ShowDirectory, View):

    def get(self, request, dataset_id=None, resource_id=None, glob_path=None, *args, **kwargs):

        get_object_or_404(Dataset, id=dataset_id)
        get_object_or_404(Resource, id=resource_id)

        self.location = os.path.join(DIRECTORY_STORAGE, resource_id)
        if not self.has_file(glob_path):
            raise Http404()

        filename = str(pathlib.Path(self.location).joinpath(glob_path))
        content_type = MimeTypes().guess_type(str(filename))[0] or mime.from_file(str(filename))

        with open(filename, 'rb') as data:
            return HttpResponse(data, content_type=content_type)


# TODO ## FACTORISER ## TODO # 


def iterate(location, base_url=None):
    files = []
    for filename in pathlib.Path(location).glob('**/[!_\.]*'):
        if not filename.is_dir():
            href = reduce(
                urljoin, [DOMAIN, base_url, str(filename.relative_to(location))])
            content_type = MimeTypes().guess_type(str(filename))[0] or mime.from_file(str(filename))
            size = filename.stat().st_size

            files.append({
                'content_type': content_type,
                'href': href,
                'size': size,
            })
    return files


def save_ckan_resource(instance, with_user=None):

    ckan_package = CkanHandler.get_package(str(instance.dataset.ckan_id))
    username = with_user and with_user.username or instance.dataset.editor.username
    apikey = CkanHandler.get_user(username)['apikey']

    location = os.path.join(DIRECTORY_STORAGE, str(instance.pk))

    base_url = reverse('idgo_resource:directory_storage', kwargs={
        'dataset_id': instance.dataset.pk,
        'resource_id': instance.pk,
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
