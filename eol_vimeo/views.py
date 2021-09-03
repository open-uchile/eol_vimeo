# -*- coding: utf-8 -*-


from django.contrib.auth.models import User

from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.conf import settings

import requests
import json
import urllib.request
import urllib.parse
import urllib.error
import base64
from django.views.generic.base import View
from cms.djangoapps.contentstore.views import videos
import os
import sys

import logging
logger = logging.getLogger(__name__)

def vimeo_api(request):
    """
        .
    """
    logger.info("EolVimeo - Request method from vimeo - {}".format(request.method))
    edx_video_id = request.GET.get('videoid', '')
    logger.info("EolVimeo - Request vimeo get video id - edx_video_id={}".format(edx_video_id))
    bucket = videos.storage_service_bucket()
    key = videos.storage_service_key(bucket, file_name=edx_video_id)
    upload_url = key.generate_url(86400, 'GET')
    logger.info("EolVimeo - Request vimeo send url video - upload_url={}".format(upload_url))
    return HttpResponseRedirect(upload_url)

