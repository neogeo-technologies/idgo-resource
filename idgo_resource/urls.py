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

from idgo_resource.views import CreateResourceFtp
from idgo_resource.views import CreateResourceUpload
from idgo_resource.views import Dashboard
from idgo_resource.views import DeleteResourceFtp
from idgo_resource.views import DeleteResourceUpload
from idgo_resource.views import EditResourceFtp
from idgo_resource.views import EditResourceUpload
from idgo_resource.views import EmitResourceFtp
from idgo_resource.views import EmitResourceUpload
from idgo_resource.views import NewResource
from idgo_resource.views import RedirectResource
from idgo_resource.views import ShowResourceFtp
from idgo_resource.views import ShowResourceUpload
from idgo_resource.views import UpdateResourceFtp
from idgo_resource.views import UpdateResourceUpload


urlpatterns = [
    url('^dataset/(?P<dataset_id>(\d+))/resource/dashboard/$', Dashboard.as_view(), name='dashboard'),

    url('^dataset/(?P<dataset_id>(\d+))/-/resource/$', RedirectResource.as_view(), name='redirect_resource'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/new/$', NewResource.as_view(), name='new_resource'),

    # Resource: Upload
    # ================
    url('^dataset/(?P<dataset_id>(\d+))/resource/new/upload/$', EmitResourceUpload.as_view(), name='emit_resource_upload'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/new/upload/create/$', CreateResourceUpload.as_view(), name='create_resource_upload'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/upload/show/$', ShowResourceUpload.as_view(), name='show_resource_upload'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/upload/edit/$', EditResourceUpload.as_view(), name='edit_resource_upload'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/upload/update/$', UpdateResourceUpload.as_view(), name='update_resource_upload'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/upload/delete/$', DeleteResourceUpload.as_view(), name='delete_resource_upload'),

    # Resource: Ftp
    # =============
    url('^dataset/(?P<dataset_id>(\d+))/resource/new/ftp/$', EmitResourceFtp.as_view(), name='emit_resource_ftp'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/new/ftp/create/$', CreateResourceFtp.as_view(), name='create_resource_ftp'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/ftp/show/$', ShowResourceFtp.as_view(), name='show_resource_ftp'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/ftp/edit/$', EditResourceFtp.as_view(), name='edit_resource_ftp'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/ftp/update/$', UpdateResourceFtp.as_view(), name='update_resource_ftp'),
    url('^dataset/(?P<dataset_id>(\d+))/resource/(?P<resource_id>(\d+))/ftp/delete/$', DeleteResourceFtp.as_view(), name='delete_resource_ftp'),
]
