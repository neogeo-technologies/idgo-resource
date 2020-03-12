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


from idgo_resource.forms.resource import ModelResourceForm
from idgo_resource.forms.ftp import CreateResourceFtpForm
from idgo_resource.forms.ftp import EditResourceFtpForm
from idgo_resource.forms.ftp import EmitResourceFtpForm
from idgo_resource.forms.ftp import ModelResourceFtpForm
from idgo_resource.forms.ftp import UpdateResourceFtpForm
from idgo_resource.forms.upload import CreateResourceUploadForm
from idgo_resource.forms.upload import EditResourceUploadForm
from idgo_resource.forms.upload import EmitResourceUploadForm
from idgo_resource.forms.upload import ModelResourceUploadForm
from idgo_resource.forms.upload import UpdateResourceUploadForm


__all__ = [
    ModelResourceForm,
    ModelResourceFtpForm,
    ModelResourceUploadForm,
    EmitResourceFtpForm,
    EmitResourceUploadForm,
    UpdateResourceFtpForm,
    UpdateResourceUploadForm,
    CreateResourceFtpForm,
    CreateResourceUploadForm,
    EditResourceFtpForm,
    EditResourceUploadForm,
]
