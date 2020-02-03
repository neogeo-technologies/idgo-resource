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
import json
import os
import shutil
from urllib.parse import urljoin
import uuid

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from idgo_admin.ckan_module import CkanHandler
from idgo_admin.ckan_module import CkanUserHandler
from idgo_admin.managers import DefaultResourceManager
from idgo_admin.utils import three_suspension_points
from idgo_resource import logger


try:
    DOWNLOAD_SIZE_LIMIT = settings.DOWNLOAD_SIZE_LIMIT
except AttributeError:
    DOWNLOAD_SIZE_LIMIT = 104857600

if settings.STATIC_ROOT:
    locales_path = os.path.join(settings.STATIC_ROOT, 'mdedit/config/locales/fr/locales.json')
else:
    locales_path = os.path.join(settings.BASE_DIR, 'idgo_admin/static/mdedit/config/locales/fr/locales.json')

try:
    with open(locales_path, 'r', encoding='utf-8') as f:
        MDEDIT_LOCALES = json.loads(f.read())
        AUTHORIZED_PROTOCOL = (
            (protocol['id'], protocol['value']) for protocol
            in MDEDIT_LOCALES['codelists']['MD_LinkageProtocolCode'])
except Exception:
    AUTHORIZED_PROTOCOL = None

CKAN_STORAGE_PATH = settings.CKAN_STORAGE_PATH
OWS_URL_PATTERN = settings.OWS_URL_PATTERN
CKAN_URL = settings.CKAN_URL


# =======================
# Modèle RESOURCE FORMATS
# =======================


class ResourceFormats(models.Model):
    """Modèle de classe des formats de données des ressources."""

    class Meta(object):
        verbose_name = "Format de ressource"
        verbose_name_plural = "Formats de ressource"

    slug = models.SlugField(
        verbose_name="Slug",
        max_length=100,
        unique=True,
        db_index=True,
    )

    description = models.TextField(
        verbose_name="Description",
    )

    extension = models.CharField(
        verbose_name="Extension du fichier",
        max_length=10,
    )

    mimetype = ArrayField(
        models.TextField(),
        verbose_name="Type MIME",
        blank=True,
        null=True,
    )

    PROTOCOL_CHOICES = AUTHORIZED_PROTOCOL

    protocol = models.CharField(
        verbose_name="Protocole",
        max_length=100,
        blank=True,
        null=True,
        choices=PROTOCOL_CHOICES,
    )

    ckan_format = models.CharField(
        verbose_name="Format CKAN",
        max_length=10,
    )

    CKAN_CHOICES = (
        (None, 'N/A'),
        ('text_view', 'text_view'),
        ('geo_view', 'geo_view'),
        ('recline_view', 'recline_view'),
        ('pdf_view', 'pdf_view'),
    )

    ckan_view = models.CharField(
        verbose_name="Vue CKAN",
        max_length=100,
        blank=True,
        null=True,
        choices=CKAN_CHOICES,
    )

    is_gis_format = models.BooleanField(
        verbose_name="Format de fichier SIG",
        blank=False,
        null=False,
        default=False,
    )

    def __str__(self):
        return self.description


# ===============
# Modèle RESOURCE
# ===============


class Resource(models.Model):
    """Modèle de classe d'une ressource de données."""

    class Meta(object):
        verbose_name = "Ressource"
        verbose_name_plural = "Ressources"

    # Managers
    # ========

    objects = models.Manager()
    default = DefaultResourceManager()

    # Champs atributaires
    # ===================

    dataset = models.ForeignKey(
        to='idgo_admin.Dataset',
        related_name='idgo_resources',
        verbose_name="Jeu de données",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    ckan_id = models.UUIDField(
        verbose_name="Ckan UUID",
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    title = models.TextField(
        verbose_name='Title',
    )

    description = models.TextField(
        verbose_name="Description",
        blank=True,
        null=True,
    )

    LANG_CHOICES = (
        ('french', "Français"),
        ('english', "Anglais"),
        ('italian', "Italien"),
        ('german', "Allemand"),
        ('other', "Autre"),
    )

    language = models.CharField(
        verbose_name="Langue",
        choices=LANG_CHOICES,
        default='french',
        max_length=10,
    )

    format_type = models.ForeignKey(
        to='ResourceFormats',
        verbose_name="Format",
        blank=False,
        null=True,
    )

    created_on = models.DateTimeField(
        verbose_name='Date de création de la resource',
        blank=True,
        null=True,
        default=timezone.now,
    )

    last_update = models.DateTimeField(
        verbose_name='Date de dernière modification de la resource',
        blank=True,
        null=True,
    )

    TYPE_CHOICES = (
        ('raw', "Données brutes"),
        ('annexe', "Documentation associée"),
        ('service', "Service"),
    )

    resource_type = models.CharField(
        verbose_name="Type de la ressource",
        choices=TYPE_CHOICES,
        max_length=10,
        default='raw',
    )

    def __str__(self):
        return self.title

    @property
    def title_overflow(self):
        return three_suspension_points(self.title)

    @property
    def ckan_url(self):
        return reduce(urljoin, [
            CKAN_URL,
            'dataset/',
            self.dataset.slug + '/',
            'resource/',
            str(self.ckan_id) + '/',
        ])

    @property
    def api_location(self):
        kwargs = {
            'dataset_name': self.dataset.slug,
            'resource_id': self.ckan_id,
        }
        return reverse('api:resource_show', kwargs=kwargs)


# ============
# Modèles liés
# ============


class AbstractResourceRelation(models.Model):
    """Classe abstraite de définition des relations entres ressource et modèles liés."""

    class Meta:
        abstract = True

    resource = models.OneToOneField(
        'idgo_resource.Resource',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )


class AbstractResourceSync(AbstractResourceRelation):
    """Classe abstraite de définition des ressources synchronisées."""

    class Meta:
        abstract = True

    synchronise = models.BooleanField(
        verbose_name="Synchronisation de données distante",
        default=False,
    )

    EXTRA_FREQUENCY_CHOICES = (
        ('5mn', "Toutes les 5 minutes"),
        ('15mn', "Toutes les 15 minutes"),
        ('20mn', "Toutes les 20 minutes"),
        ('30mn', "Toutes les 30 minutes"),
    )

    FREQUENCY_CHOICES = (
        ('1hour', "Toutes les heures"),
        ('3hours', "Toutes les trois heures"),
        ('6hours', "Toutes les six heures"),
        ('daily', "Quotidienne (tous les jours à minuit)"),
        ('weekly', "Hebdomadaire (tous les lundi)"),
        ('bimonthly', "Bimensuelle (1er et 15 de chaque mois)"),
        ('monthly', "Mensuelle (1er de chaque mois)"),
        ('quarterly', "Trimestrielle (1er des mois de janvier, avril, juillet, octobre)"),
        ('biannual', "Semestrielle (1er janvier et 1er juillet)"),
        ('annual', "Annuelle (1er janvier)"),
        ('never', "Jamais"),
    )

    sync_frequency = models.CharField(
        verbose_name="Fréquence de synchronisation",
        max_length=20,
        blank=True,
        null=True,
        choices=FREQUENCY_CHOICES + EXTRA_FREQUENCY_CHOICES,
        default='never',
    )

    url = models.URLField(
        verbose_name="Référencer une URL",
        max_length=2000,
        blank=True,
        null=True,
    )


def _ftp_file_upload_to(instance, filename):
    return filename


class AbstractResourceFile(AbstractResourceRelation):
    """Classe abstraite de définition des ressources contenant un fichier."""

    class Meta:
        abstract = True

    file_path = models.FileField(
        verbose_name="Fichier",
        blank=True,
        null=True,
        db_column='file',
        upload_to=_ftp_file_upload_to,
    )

    @property
    def get_file_url(self):
        if self.file_path and hasattr(self.file_path, 'url'):
            return self.file_path.url
        else:
            return None


class Href(AbstractResourceSync):
    """Modèle de classe les ressources référençant une URL."""

    class Meta(object):
        db_table = 'resource_href'
        verbose_name = "Ressource référençant une URL"
        verbose_name_plural = "Ressources référençant une URL"


class Download(AbstractResourceSync):
    """Modèle de classe les ressources téléchargées depuis une URL distante."""

    class Meta(object):
        db_table = 'resource_download'
        verbose_name = "Ressource Téléchargée depuis une URL distante"
        verbose_name_plural = "Ressources Téléchargées depuis une URL distante"


class Upload(AbstractResourceFile):
    """Modèle de classe les ressources téléversées."""

    class Meta(object):
        db_table = 'resource_upload'
        verbose_name = "Ressource téléversée"
        verbose_name_plural = "Ressources téléversées"


class Ftp(AbstractResourceFile):
    """Modèle de classe les ressources FTP."""

    class Meta(object):
        db_table = 'resource_ftp'
        verbose_name = "Ressource FTP"
        verbose_name_plural = "Ressources FTP"


class Store(AbstractResourceFile):
    """Modèle de classe les ressources pour le stockage de fichiers."""

    class Meta(object):
        db_table = 'resource_store'
        verbose_name = "Ressource pour le stockage de fichiers"
        verbose_name_plural = "Ressources pour le stockage de fichiers"

    @property
    def url(self):
        domain = settings.DOMAIN_NAME
        path = reverse('idgo_resource:directory_storage', kwargs={
            'dataset_id': self.resource.dataset.pk,
            'resource_id': self.resource.pk
        })
        return urljoin(domain, path)


# Signaux
# =======

@receiver(post_save, sender=Resource)
def logging_after_save(sender, instance, **kwargs):
    action = kwargs.get('created', False) and 'created' or 'updated'
    logger.info("Resource \"{pk}\" has been {action}.".format(pk=instance.pk, action=action))


@receiver(post_delete, sender=Resource)
def logging_after_delete(sender, instance, **kwargs):
    logger.info("Resource \"{pk}\" has been deleted.".format(pk=instance.pk))


@receiver(post_delete, sender=Store)
def auto_delete_file_on_store_delete(sender, instance, **kwargs):
    """Supprimer le fichier du dossier de stockage
    à la suppression d'une instance Store."""

    if hasattr(instance, 'file_path'):
        # Django > 2.x
        # instance.file_path.storage.delete(instance.file_path.name)
        # Django 1.11
        if os.path.isfile(instance.file_path.path):
            os.remove(instance.file_path.path)

    if hasattr(instance, 'resource'):
        store_path = '{}/{}'.format(settings.DIRECTORY_STORAGE, instance.resource.pk)
        shutil.rmtree(store_path)


@receiver(pre_save, sender=Store)
def auto_delete_file_on_store_change(sender, instance, **kwargs):
    """Supprimer l'ancien fichier du dossier de stockage
    à la modification d'une instance Store si le fichier est différent."""

    if not instance.pk:
        return False

    try:
        old_file = sender.objects.get(pk=instance.pk).file_path
    except sender.DoesNotExist:
        return False

    new_file = instance.file_path
    if not old_file == new_file:
        # Django > 2.x
        # instance.file_path.storage.delete(old_file.name)
        # Django 1.11
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)


@receiver(post_delete, sender=Resource)
def delete_ckan_resource(sender, instance, **kwargs):
    """Supprimer la resource CKAN à la suppression d'une resource."""
    apikey = CkanHandler.get_user(instance.dataset.editor.username)['apikey']
    with CkanUserHandler(apikey=apikey) as ckan:
        ckan.delete_resource(str(instance.ckan_id))
    logger.info("CKAN Resource \"{pk}\" has been deleted.".format(pk=instance.ckan_id))
