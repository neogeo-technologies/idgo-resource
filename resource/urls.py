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


from django.conf.urls import url

from resource.views import CreateResourceStore
from resource.views import DeleteResourceStore
from resource.views import EditResourceStore
from resource.views import EmitResourceStore
from resource.views import GoForResource
from resource.views import ShowDirectoryStorage
from resource.views import ShowDirectoryStorageGlob
from resource.views import ShowResourceStore
from resource.views import UpdateResourceStore


urlpatterns = [
    url('^dataset/(?P<dataset_id>(\d+))/resource/new/$', GoForResource.as_view(), name='go_for_resource'),

    # Resource: Store
    # ===============
    url('^dataset/(?P<dataset_id>(\d+))/resource/new/store/$', EmitResourceStore.as_view(), name='emit_resource_store'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/new/store/create/$', CreateResourceStore.as_view(), name='create_resource_store'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/store/show/$', ShowResourceStore.as_view(), name='show_resource_store'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/store/edit/$', EditResourceStore.as_view(), name='edit_resource_store'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/store/update/$', UpdateResourceStore.as_view(), name='update_resource_store'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/store/delete/$', DeleteResourceStore.as_view(), name='delete_resource_store'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/store/directory/$', ShowDirectoryStorage.as_view(), name='directory_storage'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/store/directory/(?P<glob_path>(.+))/?$', ShowDirectoryStorageGlob.as_view(), name='directory_storage_glob'),
]
