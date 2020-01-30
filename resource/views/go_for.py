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


from django.conf import settings
from django.contrib.auth.decorators import login_required
# from django.db import transaction
# from django.http import Http404
# from django.shortcuts import get_object_or_404
# from django.shortcuts import redirect
# from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
# from idgo_admin.exceptions import ExceptionsHandler
# from idgo_admin.exceptions import ProfileHttp404
from idgo_admin.models import Dataset
from idgo_admin.shortcuts import get_object_or_404_extended
# from idgo_admin.shortcuts import on_profile_http404
from idgo_admin.shortcuts import render_with_info_profile
from idgo_admin.shortcuts import user_and_profile
# from idgo_admin.views.dataset import target as datasets_target
# from resource import logger
# from resource.models import Resource


# CKAN_URL = settings.CKAN_URL
#
# FTP_DIR = settings.FTP_DIR
# try:
#     FTP_UPLOADS_DIR = settings.FTP_UPLOADS_DIR
# except AttributeError:
#     FTP_UPLOADS_DIR = 'uploads'


decorators = [csrf_exempt, login_required(login_url=settings.LOGIN_URL)]


@method_decorator(decorators, name='dispatch')
class GoForResource(View):

    def get(self, request, dataset_id=None, *args, **kwargs):
        user, profile = user_and_profile(request)
        dataset = get_object_or_404_extended(Dataset, user, include={'id': dataset_id})
        context = {'dataset': dataset}
        return render_with_info_profile(request, 'resource/go_for.html', context)

    # def post(self, request, dataset_id=None, *args, **kwargs):
    #     # redirect to resource children app:
    #     app = request.POST.get('app', request.GET.get('app'))
    #     if app:
    #         return redirect(self.resource_router(dataset_id, app, action='create'))


# @method_decorator(decorators, name='dispatch')
# class ResourceManager(View):
#     template = 'resource/resource.html'
#
#     def get_context(self, form, user, dataset, resource=None):
#         return {
#             'target': datasets_target(dataset, user),
#             'dataset': dataset,
#             'resource': resource,
#             'form': form,
#             }
#
#     def resource_router(self, dataset_id, app, instance_id=None, action='create'):
#         from django.apps import apps
#         from django.urls.exceptions import NoReverseMatch
#         if apps.is_installed(app):
#             url_pattern = "{0}:resource-{0}-{1}".format(app, action)
#             kvp = {'dataset_id': dataset_id}
#             if action == 'update':
#                 kvp['pk'] = instance_id
#             return reverse(url_pattern, kwargs=kvp)
#         else:
#             raise NoReverseMatch
#
#     @ExceptionsHandler(actions={ProfileHttp404: on_profile_http404})
#     def get(self, request, dataset_id=None, *args, **kwargs):
#
#         user, profile = user_and_profile(request)
#
#         dataset = get_object_or_404_extended(
#             Dataset, user, include={'id': dataset_id})
#         # redirect to resource children app:
#         app = request.POST.get('app', request.GET.get('app'))
#         if app:
#             return redirect(self.resource_router(dataset_id, app, action='create'))
#         # Redirect to layer
#         # _resource = request.GET.get('resource')
#         # _layer = request.GET.get('layer')
#         # if _resource and _layer:
#         #     return redirect(
#         #         reverse('idgo_admin:layer_editor', kwargs={
#         #             'dataset_id': dataset.id,
#         #             'resource_id': _resource,
#         #             'layer_id': _layer}))
#         #
#         # resource = None
#         # id = request.GET.get('id')
#         # if id:
#         #     include = {'id': id, 'dataset_id': dataset.id}
#         #     resource = get_object_or_404_extended(Resource, user, include=include)
#
#         # form = Form(instance=resource)
#         context = self.get_context(None, user, dataset, resource=resource)
#         return render_with_info_profile(request, self.template, context)
#
#     @ExceptionsHandler(ignore=[Http404], actions={ProfileHttp404: on_profile_http404})
#     @transaction.atomic
#     def post(self, request, dataset_id=None, *args, **kwargs):
#         user, profile = user_and_profile(request)
#         dataset = get_object_or_404_extended(
#             Dataset, user, include={'id': dataset_id})
#         form = Form(request.POST, request.FILES)
#         if form.is_valid():
#
#             try:
#                 resource = form.save()
#             except Exception:
#                 logger.excption('ResourceManager:post')
#             else:
#                 app = request.POST.get('app')
#                 return redirect(self.resource_router(dataset_id, app, action='create'))
#
#         context = self.get_context(form, user, dataset, resource)
#         return render_with_info_profile(request, self.template, context)


# @login_required(login_url=settings.LOGIN_URL)
# @csrf_exempt
# def resource(request, dataset_id=None, *args, **kwargs):
#     user, profile = user_and_profile(request)
#
#     id = request.GET.get('id', request.GET.get('ckan_id'))
#     if not id:
#         raise Http404()
#
#     kvp = {}
#     try:
#         id = int(id)
#     except ValueError:
#         kvp['ckan_id'] = id
#     else:
#         kvp['id'] = id
#     finally:
#         resource = get_object_or_404(Resource, **kvp)
#
#     # TODO:
#     # return redirect(reverse('idgo_admin:resource_editor', kwargs={
#     #     'dataset_id': resource.dataset.id, 'resource_id': resource.id}))
#     return redirect(
#         '{}?id={}'.format(
#             reverse(
#                 'resource:resource', kwargs={'dataset_id': resource.dataset.id}),
#             resource.id))