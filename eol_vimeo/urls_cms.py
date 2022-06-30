

from django.conf.urls import url
from django.conf import settings

from .views import vimeo_callback, vimeo_update_picture

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

urlpatterns = (
    url(
        r'^eolvimeo/callback',
        vimeo_callback,
        name='vimeo_callback',
    ),
    url(
        r'^eolvimeo/update_picture',
        vimeo_update_picture,
        name='vimeo_update_picture',
    ),
)
