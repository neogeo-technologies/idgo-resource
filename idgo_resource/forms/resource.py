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


from django.apps import apps
from django import forms
from django.forms.models import ModelChoiceIterator

from idgo_resource import logger
from idgo_resource.models import Resource
from idgo_resource.models import ResourceFormats
from idgo_resource.redis_client import Handler as RedisHandler


class FormatTypeSelect(forms.Select):

    @staticmethod
    def _choice_has_empty_value(choice):
        """Return True if the choice's value is empty string or None."""
        value, _, extension = choice
        return value is None or value == ''

    def optgroups(self, name, value, attrs=None):
        """Return a list of optgroups for this widget."""
        groups = []
        has_selected = False

        for index, (option_value, option_label, option_extension) in enumerate(self.choices):
            if option_value is None:
                option_value = ''

            subgroup = []
            if isinstance(option_label, (list, tuple)):
                group_name = option_value
                subindex = 0
                choices = option_label
            else:
                group_name = None
                subindex = None
                choices = [(option_value, option_label, option_extension)]
            groups.append((group_name, subgroup, index))

            for subvalue, sublabel, subextra in choices:
                selected = (
                    str(subvalue) in value and
                    (not has_selected or self.allow_multiple_selected))

                has_selected |= selected
                subgroup.append(
                    self.create_option(
                        name, subvalue, sublabel, selected, index,
                        subindex=subindex, extension=option_extension))
                if subindex is not None:
                    subindex += 1
        return groups

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None, extension=None):
        result = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if extension:
            result['attrs']['extension'] = extension
        return result


class ModelFormatIterator(ModelChoiceIterator):

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ('', self.field.empty_label, '')
        queryset = self.queryset
        if not queryset._prefetch_related_lookups:
            queryset = queryset.iterator()
        for obj in queryset:
            yield self.choice(obj)

    def choice(self, obj):
        _extension = obj.ckan_format.lower() and obj.extension or ''

        return (
            self.field.prepare_value(obj),
            self.field.label_from_instance(obj),
            obj.extension.lower() == _extension
        )


class ModelFormatTypeField(forms.ModelChoiceField):
    iterator = ModelFormatIterator


class ModelResourceForm(forms.ModelForm):

    class Meta(object):
        model = Resource
        fields = (
            'title',
            'description',
            'language',
            'format_type',
            'resource_type',
            'redis_key',
        )

    title = forms.CharField(
        label='Titre*',
        required=True,
        widget=forms.TextInput(
            attrs={
                'placeholder': "Titre",
            },
        ),
    )

    description = forms.CharField(
        label="Description",
        required=False,
        widget=forms.Textarea(
            attrs={
                'placeholder': "Vous pouvez utiliser le langage Markdown ici",
            },
        ),
    )

    language = forms.ChoiceField(
        label="Langue",
        required=True,
        choices=Meta.model.LANG_CHOICES,
    )

    resource_type = forms.ChoiceField(
        label="Type",
        required=True,
        choices=Meta.model.TYPE_CHOICES,
    )

    format_type = ModelFormatTypeField(
        label="Format*",
        empty_label="Sélectionnez un format",
        required=True,
        queryset=ResourceFormats.objects.all().order_by('extension'),
        widget=FormatTypeSelect(),
    )

    redis_key = forms.CharField(required=False)

    def set_related_resource(self, model_name, pk, app_label='idgo_resource'):
        try:
            RelatedModel = apps.get_model(
                app_label=app_label, model_name=model_name)
            instance = RelatedModel.objects.get(pk=pk)
            instance.resource = self.instance
        except RelatedModel.DoesNotExist:
            logger.error(
                "Resource File not found: model {model} - pk {pk}".format(
                    model=model_name, pk=pk))
        else:
            instance.save()

    def save(self, *args, commit=True, **kwargs):
        kwargs.setdefault('app_label', 'idgo_resource')

        resource = self.instance
        resource.dataset = kwargs['dataset']

        resource.save()

        redis_key = self.cleaned_data.get('redis_key')
        if redis_key:
            data = RedisHandler().update(redis_key, resource_pk=resource.pk)
            model_name = data['related_model']
            pk = data['related_pk']
            app_label = kwargs['app_label']
            self.set_related_resource(model_name, pk, app_label=app_label)

        return resource
