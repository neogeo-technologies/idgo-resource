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
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from idgo_admin.shortcuts import user_and_profile
from idgo_resource.models import Resource


decorators = [csrf_exempt, login_required(login_url=settings.LOGIN_URL)]


@method_decorator(decorators, name='dispatch')
class ShowResource(View):
    """Voir une resource."""


@method_decorator(decorators, name='dispatch')
class RedirectResource(View):
    """Rediriger vers la resource."""

    def get(self, request, dataset_id=None, *args, **kwargs):
        user, profile = user_and_profile(request)

        id = request.GET.get('id', request.GET.get('ckan_id'))
        if not id:
            raise Http404()

        kwargs = {}
        try:
            id = int(id)
        except ValueError:
            kwargs['ckan_id'] = id
        else:
            kwargs['id'] = id
        resource = get_object_or_404(Resource, **kwargs)

        if hasattr(resource, 'store'):
            namespace = 'resource:show_resource_store'
        else:
            raise Http404()

        url = reverse(namespace, kwargs={'dataset_id': resource.dataset.pk, 'resource_id': resource.pk})
        return redirect(url)
