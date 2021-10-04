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
from django.utils import timezone
import datetime
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
    if 'token' not in request.GET:
        return HttpResponse(status=400)
    edx_video_id = request.GET.get('videoid', '')
    token = request.GET.get('token', '')
    if not EolVimeoVideo.objects.filter(edx_video_id=edx_video_id, status__in=['vimeo_encoding', 'vimeo_upload', 'upload_completed_encoding'], token=token).exists():
        logger.error("EolVimeo - Video id have problem, check model, edx_video_id: {}, token: {}".format(edx_video_id, token))
        return HttpResponse(status=400)
    video_vimeo = EolVimeoVideo.objects.get(edx_video_id=edx_video_id, token=token)
    now = timezone.now()
    if now >= video_vimeo.expiry_at:
        logger.error("EolVimeo - expiration date is greater than or equal datetime now, edx_video_id: {}, now: {}, expiry_at: {}".format(edx_video_id, now, video_vimeo.expiry_at))
        return HttpResponse(status=400)
    upload_url = get_url_video(edx_video_id)
    return HttpResponseRedirect(upload_url)

def get_url_video(edx_video_id):
    bucket = videos.storage_service_bucket()
    key = videos.storage_service_key(bucket, file_name=edx_video_id)
    upload_url = key.generate_url(86400, 'GET')
    return upload_url