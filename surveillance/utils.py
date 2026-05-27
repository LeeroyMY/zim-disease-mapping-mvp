import os
import subprocess
from django.conf import settings
from django.apps import apps
from django.db import models
from .models import BaseDiseaseCase

def get_or_create_dynamic_model(disease_type, extra_columns):
    """
    Returns the appropriate Django model class for a given disease type.

    Routes the five core diseases to their dedicated concrete models.
    Any other disease type falls back to GenericDiseaseCase, which stores
    arbitrary extra columns in a JSONB field to avoid schema migrations.
    """
    class_name_lower = "".join([c for c in disease_type.title() if c.isalpha()]).lower() + "case"

    MODEL_MAP = {
        'choleracase':  'choleracase',
        'hivcase':      'hivcase',
        'tbcase':       'tbcase',
        'malariacase':  'malariacase',
        'typhoidcase':  'typhoidcase',
    }

    app_label = MODEL_MAP.get(class_name_lower, 'genericdiseasecase')
    return apps.get_model('surveillance', app_label)
