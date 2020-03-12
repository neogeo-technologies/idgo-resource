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


from functools import reduce
from operator import ior

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse

from idgo_admin.models import Dataset
from idgo_admin.shortcuts import render_with_info_profile
from idgo_admin.shortcuts import user_and_profile
from idgo_resource.forms import CreateResourceUploadForm
from idgo_resource.forms import EditResourceUploadForm
from idgo_resource.forms import EmitResourceUploadForm
from idgo_resource.forms import UpdateResourceUploadForm
from idgo_resource.models import ResourceFormats
from idgo_resource.models import Resource
from idgo_resource.redis_client import Handler as RedisHandler


LOGIN_URL = settings.LOGIN_URL
decorators = [csrf_exempt, login_required(login_url=LOGIN_URL)]


@method_decorator(decorators, name='dispatch')
class ResourceUploadBaseView(View):

    CreateResourceForm = CreateResourceUploadForm
    default_resource_type = 'raw'

    def get(self, *args, **kwargs):
        raise NotImplementedError

    def post(self, *args, **kwargs):
        raise NotImplementedError

    def redis_create_key(self, user, instance, instance_pk, content_type):
        return RedisHandler().create(
            user=user.pk,
            content_type=content_type,
            name=instance.file_path.name,
            size=instance.file_path.size,
            filename=instance.file_path.path,
            related_pk=instance_pk,
            related_model=type(instance).__name__
        )

    def init_resource_form(self, instance, title, content_type, redis_key, resource=None):

        filters = [
            Q(mimetype__overlap=[content_type]),
            Q(extension=instance.file_path.name.split('.')[-1])
        ]
        format_type = ResourceFormats.objects.filter(reduce(ior, filters)).distinct().first()

        resource_form = self.CreateResourceForm(
            # instance=resource,  # Si on veut recuperer les anciennes valeurs
            initial={
                'title': title,
                'language': 'french',
                'resource_type': self.default_resource_type,
                'format_type': format_type,
                'redis_key': redis_key,
                'description': resource.description if resource else ''
            }
        )
        return resource_form


class EmitResourceUpload(ResourceUploadBaseView):
    """Emettre un fichier pour la création d'une ressource de type Upload."""

    EmitResourceForm = EmitResourceUploadForm
    template_emit = 'resource/upload/emit.html'
    template_create = 'resource/upload/create.html'

    def get(self, request, dataset_id=None, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404(Dataset, pk=dataset_id)
        form = self.EmitResourceForm()

        context = {'form': form, 'extensions': form.extensions, 'dataset': dataset}
        return render_with_info_profile(request, self.template_emit, context)

    @transaction.atomic
    def post(self, request, dataset_id=None, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404(Dataset, pk=dataset_id)
        form = self.EmitResourceForm(data=request.POST, files=request.FILES)

        if not form.is_valid():
            context = {'form': form, 'dataset': dataset}
            return render_with_info_profile(request, self.template_emit, context)

        instance = form.save()

        content_type = request.FILES.get('file_path').content_type
        title = request.FILES.get('file_path').name

        # Création d'une entrée REDIS pour suivre la vie de la création de la ressource
        redis_key = self.redis_create_key(user, instance, instance.pk, content_type)

        resource_form = self.init_resource_form(instance, title, content_type, redis_key)

        msg = "Veuillez vérifier les informations pré-remplies ci-dessous avant de la valider la création."
        messages.info(request, msg)

        context = {'form': resource_form, 'dataset': dataset}
        return render_with_info_profile(request, self.template_create, context)


class UpdateResourceUpload(ResourceUploadBaseView):
    """Emettre un nouveau fichier pour une ressource de type Upload."""

    UpdateResourceForm = UpdateResourceUploadForm
    template_update = 'resource/upload/update.html'
    template_edit = 'resource/upload/edit.html'
    related_attr = 'upload'

    def get(self, request, dataset_id, resource_id, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404(Dataset, pk=dataset_id)
        resource = get_object_or_404(Resource, pk=resource_id)

        instance = getattr(resource, self.related_attr)
        context = {
            'form': self.UpdateResourceForm(instance=instance),
            'dataset': dataset,
            'resource': resource,
            'upload': instance,
        }
        return render_with_info_profile(request, self.template_update, context)

    @transaction.atomic
    def post(self, request, dataset_id, resource_id, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404(Dataset, pk=dataset_id)
        resource = get_object_or_404(Resource, pk=resource_id)

        instance = getattr(resource, self.related_attr)
        form = self.UpdateResourceForm(
            data=request.POST, files=request.FILES, instance=instance)

        if not form.is_valid():
            context = {
                'form': form,
                'dataset': dataset,
                'resource': resource,
                'upload': instance,
            }
            return render_with_info_profile(request, self.template_update, context)

        # else:
        updated_upload = form.save()

        content_type = request.FILES.get('file_path').content_type
        title = request.FILES.get('file_path').name

        # Création d'une entrée REDIS pour suivre la vie de la création de la ressource
        redis_key = self.redis_create_key(user, updated_upload, updated_upload.pk, content_type)

        resource_form = self.init_resource_form(updated_upload, title, content_type, redis_key, resource)

        msg = "Veuillez vérifier les informations pré-remplies ci-dessous avant de la valider la création."
        messages.info(request, msg)

        context = {
            'form': resource_form,
            'dataset': dataset,
            'resource': resource,
            'upload': updated_upload,
        }
        return render_with_info_profile(request, self.template_edit, context)


@method_decorator(decorators, name='dispatch')
class CreateResourceUpload(View):
    """Créer une ressource de type Upload."""

    CreateResourceForm = CreateResourceUploadForm
    template = 'resource/create_upload.html'
    viewname = 'idgo_resource:show_resource_upload'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form = None

    @transaction.atomic
    def post(self, request, dataset_id=None, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404(Dataset, pk=dataset_id)

        self.form = self.CreateResourceForm(data=request.POST)

        context = {'form': self.form, 'dataset': dataset}
        if not self.form.is_valid():
            return render_with_info_profile(request, self.template, context)

        resource = self.form.save(dataset=dataset)

        redis_key = self.form.cleaned_data.get('redis_key')
        self.run_asynchronous_tasks(redis_key)

        ###
        # msg = (
        #     'La ressource a été créée avec succès. '
        #     'Souhaitez-vous <a href="{0}">ajouter une nouvelle ressource</a> '
        #     'ou bien <a href="{1}" target="_blank">voir la ressource dans CKAN</a> ?'
        # ).format(
        #     reverse('idgo_admin:resource', kwargs={'dataset_id': dataset.pk}),
        #     resource.ckan_url,
        # )
        # messages.success(request, msg)
        #
        # kwargs = {'dataset_id': dataset_id, 'resource_id': resource.pk}
        # url = reverse(self.viewname, kwargs=kwargs)
        # return HttpResponseRedirect(url)
        ###

        msg = "Création de la ressource en cours d'execution.".format(id=resource.pk)
        messages.success(request, msg)

        # url = reverse('idgo_resource:dashboard', kwargs={'dataset_id': dataset.pk})
        url = '{base_url}?id={dataset_id}#resources_store/{resource_id}'.format(
            base_url=reverse('idgo_admin:dataset'),
            dataset_id=dataset.pk,
            resource_id=resource.pk)
        return HttpResponseRedirect(url)

    def run_asynchronous_tasks(self, redis_key, *args, **kwargs):
        raise NotImplementedError('TODO')


@method_decorator(decorators, name='dispatch')
class EditResourceUpload(View):
    """Editer d'une resource de type Upload."""

    EditResourceForm = EditResourceUploadForm
    viewname = 'idgo_resource:show_resource_upload'
    template = 'resource/upload/edit.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form = None

    def get(self, request, dataset_id, resource_id, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404(Dataset, pk=dataset_id)
        resource = get_object_or_404(Resource, pk=resource_id)

        form = self.EditResourceForm(instance=resource)

        context = {'form': form, 'dataset': dataset, 'resource': resource}
        return render_with_info_profile(request, self.template, context)

    @transaction.atomic
    def post(self, request, dataset_id, resource_id, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404(Dataset, pk=dataset_id)
        resource = get_object_or_404(Resource, pk=resource_id)

        self.form = self.EditResourceForm(data=request.POST, instance=resource)

        if not self.form.is_valid():
            context = {'form': self.form, 'dataset': dataset, 'resource': resource}
            return render_with_info_profile(request, self.template, context)

        resource = self.form.save(dataset=dataset)

        redis_key = self.form.cleaned_data.get('redis_key')
        if redis_key:
            self.run_asynchronous_tasks(redis_key)

        # ###
        # msg = (
        #     'La ressource a été mise à jour avec succès. '
        #     'Souhaitez-vous <a href="{0}">ajouter une nouvelle ressource</a> '
        #     'ou bien <a href="{1}" target="_blank">voir la ressource dans CKAN</a> ?'
        # ).format(
        #     reverse('idgo_admin:resource', kwargs={'dataset_id': dataset.pk}),
        #     resource.ckan_url,
        # )
        # messages.success(request, msg)
        #
        # kwargs = {'dataset_id': dataset_id, 'resource_id': resource.pk}
        # url = reverse(self.viewname, kwargs=kwargs)
        # return HttpResponseRedirect(url)
        # ###

        msg = "Mise à jour de la ressource en cours d'execution."
        messages.success(request, msg)

        # url = reverse('idgo_resource:dashboard', kwargs={'dataset_id': dataset.pk})
        url = '{base_url}?id={dataset_id}#resources_store/{resource_id}'.format(
            base_url=reverse('idgo_admin:dataset'),
            dataset_id=dataset.pk,
            resource_id=resource.pk)
        return HttpResponseRedirect(url)

    def run_asynchronous_tasks(self, redis_key, *args, **kwargs):
        raise NotImplementedError('TODO')


@method_decorator(decorators, name='dispatch')
class ShowResourceUpload(View):
    """Voir une ressource de type Upload."""

    template_show = 'resource/upload/show.html'

    def get_context(self, dataset, resource):
        return {'dataset': dataset, 'resource': resource}

    def get(self, request, dataset_id, resource_id, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404(Dataset, pk=dataset_id)
        resource = get_object_or_404(Resource, pk=resource_id)

        context = self.get_context(dataset, resource)
        return render_with_info_profile(request, self.template_show, context)


@method_decorator(decorators, name='dispatch')
class DeleteResourceUpload(View):
    """Supprimer une ressource de type Upload."""

    @transaction.atomic
    def get(self, request, dataset_id, resource_id, *args, **kwargs):
        user, profile = user_and_profile(request)

        dataset = get_object_or_404(Dataset, pk=dataset_id)
        resource = get_object_or_404(Resource, pk=resource_id)

        instance = resource.upload if hasattr(resource, 'upload') else None
        if instance:
            resource.upload.delete()
        resource.delete()

        kwargs = {'id': dataset.id}
        url = reverse('idgo_admin:dataset_editor', kwargs=kwargs)
        return HttpResponseRedirect(url)
