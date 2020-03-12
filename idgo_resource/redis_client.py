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


import json
from uuid import uuid4

from django.conf import settings
import redis

from idgo_resource import logger


REDIS_EXPIRATION = 60*60


class Handler:
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    def __init__(self, *args, **kwargs):
        try:
            kwargs.setdefault('host', settings.REDIS_HOST)
            kwargs.setdefault('port', settings.REDIS_PORT)
        except AttributeError:
            logger.warning("REDIS settings are missing in this context. Trying to connect with defaults values.")
            logger.warning("REDIS client try to connect with defaults host and port.")
        kwargs.setdefault('decode_responses', True)  # Oui decode moi tout
        self.client = redis.StrictRedis(**kwargs)

    def scent(self):
        pubsub = self.client.pubsub()
        psubscription = {
            '__keyevent@0__:expired': self.erase  # Callback qui devrait supprimer propremement les fichiers physiques.
        }
        pubsub.psubscribe(**psubscription)
        self.thread = pubsub.run_in_thread(sleep_time=0.1)

    def erase(self, msg):
        # Récupérer le path du fichier à supprimer du disque.
        self.thread.stop()

    def create(self, *args, **kwargs):
        key = uuid4().__str__()
        self.client.set(key, json.dumps(kwargs))
        self.client.expire(key, REDIS_EXPIRATION)
        return key

    def update(self, key, *args, **kwargs):
        data = self.retreive(key)
        data.update(**kwargs)
        self.client.set(key, json.dumps(data))
        return self.retreive(key)

    def retreive(self, key, *args, **kwargs):
        value = self.client.get(key)
        return json.loads(value)
