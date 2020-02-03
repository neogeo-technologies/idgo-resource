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


from idgo_resource.views.go_for import GoForResource
from idgo_resource.views.resource import RedirectResource
from idgo_resource.views.store import CreateResourceStore
from idgo_resource.views.store import EditResourceStore
from idgo_resource.views.store import EmitResourceStore
from idgo_resource.views.store import DeleteResourceStore
from idgo_resource.views.store import ShowDirectoryStorage
from idgo_resource.views.store import ShowDirectoryStorageGlob
from idgo_resource.views.store import ShowResourceStore
from idgo_resource.views.store import UpdateResourceStore


__all__ = [
    CreateResourceStore,
    EditResourceStore,
    EmitResourceStore,
    DeleteResourceStore,
    GoForResource,
    RedirectResource,
    ShowDirectoryStorage,
    ShowDirectoryStorageGlob,
    ShowResourceStore,
    UpdateResourceStore,
]