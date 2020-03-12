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
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View

from idgo_admin.models import Dataset
from idgo_admin.shortcuts import render_with_info_profile
from idgo_admin.shortcuts import user_and_profile


decorators = [csrf_exempt, login_required(login_url=settings.LOGIN_URL)]


@method_decorator(decorators, name='dispatch')
class Dashboard(View):

    def get(self, request, dataset_id=None, *args, **kwargs):
        user, profile = user_and_profile(request)
        dataset = get_object_or_404(Dataset, pk=dataset_id)

        context = {
            'dataset': dataset,
        }

        return render_with_info_profile(request, 'resource/dashboard.html', context)
