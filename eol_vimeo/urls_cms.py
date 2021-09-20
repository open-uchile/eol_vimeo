

from django.conf.urls import url
from django.conf import settings

from .views import vimeo_callback

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

urlpatterns = (
    url(
        r'^eolvimeo/callback',
        vimeo_callback,
        name='vimeo_callback',
    ),
)
