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
from eol_vimeo.models import EolVimeoVideo
import os
import sys

import logging
logger = logging.getLogger(__name__)

def vimeo_callback(request):
    """
        Get url to download video 
    """
    if request.method != "GET":
        return HttpResponse(status=400)
    if 'videoid' not in request.GET:
        return HttpResponse(status=400)

    try:
        logger.info("EolVimeo - Request origin: {}".format(request.headers['Origin']))
    except Exception:
        logger.info("EolVimeo - Error Request origin")
    try:
        logger.info("EolVimeo - Request meta: {}".format(request.META['HTTP_REFERER']))
    except Exception:
        logger.info("EolVimeo - Error Request meta")
    edx_video_id = request.GET.get('videoid', '')
    if not EolVimeoVideo.objects.filter(edx_video_id=edx_video_id, status__in=['vimeo_encoding', 'upload']).exists():
        logger.error("EolVimeo - Video id have problem check model edx_video_id: {}".format(edx_video_id))
        return HttpResponse(status=400)
    bucket = videos.storage_service_bucket()
    key = videos.storage_service_key(bucket, file_name=edx_video_id)
    upload_url = key.generate_url(86400, 'GET')
    return HttpResponseRedirect(upload_url)

