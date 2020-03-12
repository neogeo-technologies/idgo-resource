from django.conf import settings


def list_resource_extensions(request):
    """
    En considerant une liste regroupant les extensions de resource:
    RESOURCE_EXTENSIONS = ['resource_store', ...]
    INSTALLED_APPS = CORE_APPS + ... + RESOURCE_EXTENSIONS

    A charger dans les settings:
    TEMPLATES = [
        {
            # ...
            'OPTIONS': {
                'context_processors': [
                    # ...
                    'idgo_resource.context_processors.liste_resource_extensions'
                ],
            },
        },
    ]
    Permet d'avoir la variable 'RESOURCE_EXTENSIONS' accessible depuis tous les
    templates.
    """

    return {
        'RESOURCE_EXTENSIONS': [
            {
                'name': app,
                'template': 'store/butt_extent.html'
            } for app in getattr(settings, 'RESOURCE_EXTENSIONS', [])
        ]
    }
