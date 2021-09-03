

from django.conf.urls import url
from django.conf import settings

from .views import vimeo_api

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

urlpatterns = (
    url(
        r'^vimeo/api',
        vimeo_api,
        name='vimeo_api',
    ),
)
