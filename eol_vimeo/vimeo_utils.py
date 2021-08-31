# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import six
import json
import os
import math
from django.conf import settings
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys import InvalidKeyError
from django.contrib.auth.models import User
from django.urls import reverse
from lms.djangoapps.courseware.access import has_access, get_user_role
from collections import OrderedDict, defaultdict, deque
from opaque_keys.edx.locator import CourseLocator, BlockUsageLocator
from django.db import IntegrityError, transaction
from django.utils.translation import ugettext_noop
from uuid import uuid4
import logging
import vimeo
import tempfile
import shutil
import json
import urllib.parse
import requests
from edxval.models import Video
from edxval.api import update_video, _get_video, get_video_info
from django.core.files.storage import get_storage_class
from .models import EolVimeoVideo
from cms.djangoapps.contentstore.views import videos

logger = logging.getLogger(__name__)

def get_storage():
    """
        Get the default storage
    """
    return get_storage_class(settings.VIMEO_STORAGE_CLASS['class'])(**settings.VIMEO_STORAGE_CLASS['options'])

def check_credentials():
    """
        Check if credentials are defined
    """
    return settings.EOL_VIMEO_CLIENT_TOKEN != '' and settings.EOL_VIMEO_CLIENT_ID != '' and settings.EOL_VIMEO_CLIENT_SECRET != ''

def get_client_vimeo():
    if not check_credentials():
        logger.info('EolVimeo - Credentials are not defined')
        return None
    client = vimeo.VimeoClient(
        token=settings.EOL_VIMEO_CLIENT_TOKEN,
        key=settings.EOL_VIMEO_CLIENT_ID,
        secret=settings.EOL_VIMEO_CLIENT_SECRET
    )
    return client

def copy_file(id_file):
    """
        Copy the video file to a temporary directory to get the video path and upload it to vimeo
        return video uri
    """
    try:
        bucket = videos.storage_service_bucket()
        key = videos.storage_service_key(bucket, file_name=id_file)
        upload_url = key.generate_url(86400, 'GET')
        status = upload(upload_url, id_file)
        #get_storage().delete(id_file)
        return status
    except Exception:
        #IOError, ClientError
        logger.info('EolVimeo - The id_file does not exists, id_file: {}'.format(id_file))
        return 'Error'

def update_edxval_url(edx_video_id, video_url, file_size, file_name, duration, status):
    """
        Update video in edxval model with vimeo url
    """
    data = {
        "encoded_videos": [
            {
            "url": video_url,
            "file_size": file_size,
            "bitrate": 30,
            "profile": "desktop_mp4"
            }
        ],
        "client_video_id": file_name,
        "edx_video_id": edx_video_id,
        "duration": duration,
        "status": status
    }
    try:
        aux_id = update_video(data)
        return True
    except Exception as e:
        logger.exception('EolVimeo - Error to update video path, id_video: {}, exception: {}'.format(edx_video_id, str(e)))
        return False

def add_domain_to_video(video_id):
    """
        This method adds the specified domain to a video's whitelist.
    """
    client = get_client_vimeo()
    if client is None:
        return False
    domains = settings.EOL_VIMEO_DOMAINS
    is_added = True
    for domain in domains:
        response = client.put('/videos/{}/privacy/domains/{}'.format(video_id, domain))
        if response.status_code == 204:
            logger.info('EolVimeo - Domain {} added to video {} on vimeo'.format(domain, video_id))
        else:
            is_added = False
            logger.info('EolVimeo - The domain "{}" was not added to the video {} on vimeo, response: {}'.format(domain, video_id, response.json()))
    return is_added

def get_video_vimeo(id_video):
    """
        Get the video data from vimeo
    """
    client = get_client_vimeo()
    if client is None:
        return {}
    try:
        response = client.get('/videos/{}'.format(id_video), params={"fields": "name,duration,files"})
        if response.status_code == 200:
            return response.json()
        else:
            logger.info('EolVimeo - The video does not exists, id_video_vimeo:{}, response: {}'.format(id_video, response.json()))
            return {}
    except Exception as e:
        logger.exception('EolVimeo - Exception: %s' % str(e))
        return {}

def move_to_folder(id_video, name_folder):
    """
        Check if main folder exists in vimeo to move the video there, if not exists, create the folder
        Only check first 100 folders in ascending order
    """
    client = get_client_vimeo()
    if client is None:
        return False
    next_response = True
    uri_folder = ''
    uri_folder, next_response = get_folders(1, client, name_folder)
    if uri_folder == 'Error':
        return False
    if uri_folder == '':
        logger.info('EolVimeo - Vimeo folder not found')
        uri_folder = create_folder(client, name_folder)
        if uri_folder == 'Error':
            return False
    id_folder = uri_folder.split('/')[-1]
    return move_video(client, id_folder, id_video)
    
def move_video(client, id_folder, id_video):
    """
        Move id_video to id_folder
    """
    try:
        response_folder = client.put('/me/projects/{}/videos/{}'.format(id_folder,id_video))
        if response_folder.status_code == 204:
            return True
        else:
            logger.info('EolVimeo - Error to move video, id_video: {}, id_folder: {}, response: {}'.format(id_video, id_folder, response_folder.json()))
            return False
    except Exception as e:
        logger.exception('EolVimeo - Exception: %s' % str(e))
        return False

def create_folder(client, name_folder):
    """
        Create folder in vimeo.
        return folder uri
    """
    try:
        response_folder = client.post('/me/projects', data={"name": name_folder})
        if response_folder.status_code == 201:
            data_folder = response_folder.json()
            return data_folder['uri']
        else:
            logger.info('EolVimeo - Error to create folder, response: {}'.format(response_folder.json()))
            return 'Error'
    except Exception as e:
        logger.exception('EolVimeo - Exception: %s' % str(e))
        return 'Error'

def get_folders(page, client, name_folder):
    """
        Get the folders based on the given page.
        100 folders by page
    """
    uri_folder = ''
    next_step = False
    try:
        response_folder = client.get('/me/projects', params={"direction": "asc", "page":page, "per_page": 100, "sort":"name", "fields": "uri,name"})
        if response_folder.status_code == 200:
            data_folder = response_folder.json()
            next_step = data_folder['page'] < data_folder['total']
            for folder in data_folder['data']:
                if folder['name'] == name_folder:
                    uri_folder = folder['uri']
                    break
            return uri_folder, next_step
        else:
            logger.info('EolVimeo - Error to get folders, page:{}, response: {}'.format(page, response_folder.json()))
            return 'Error', next_step
    except Exception as e:
        logger.exception('EolVimeo - Exception: %s' % str(e))
        return 'Error', next_step

def upload(upload_url, id_file):
    """
        Upload the video file to Vimeo
    """
    if not check_credentials():
        logger.info('EolVimeo - Credentials are not defined')
        return 'Error'
    try:
        video = _get_video(id_file)
        headers = {
            "Authorization": "Bearer {}".format(settings.EOL_VIMEO_CLIENT_TOKEN),
            "Content-Type": "application/json",
            "Accept": 'application/vnd.vimeo.*+json;version=3.4'
        }

        url = "https://api.vimeo.com/me/videos"
        body = {
            "upload": {
                "approach": "pull",
                "link": urllib.parse.quote(upload_url, safe='/')
            },
            'name': video.client_video_id,
            'description': "",
            'privacy': {
                'embed': "whitelist",
                'view': 'disable'
                }
            }
        r = requests.post(url, data=json.dumps(body), headers=headers)
        if r.status_code == 201:
            data = json.loads(result.text)
            uri = data['uri']
            logger.info('EolVimeo - "{}" is uploading to {}'.format(id_file, uri))
            return uri
        else:
            logger.info('EolVimeo - "{}" fail upload to vimeo, status_code: {}, error: {}'.format(id_file, r.status_code, r.text))
            return 'Error'
    except (Exception, vimeo.exceptions.VideoUploadFailure) as e:
        logger.exception('EolVimeo - Error uploading: {}, Exception'.format(id_file, str(e)))
        return 'Error'

def get_link_video(video_data):
    """
        video_data['files'] has different links depending on the video quality (resolution and fps)
        this function return 720p30fps or 720p60fps or best quality link
    """
    video30 = {}
    video60 = {}
    for video in video_data['files']:
        if video['quality'] == 'hd' and video['height'] == 720 and video['fps'] < 32:
            video30 = video
        if video['quality'] == 'hd' and video['height'] == 720 and video['fps'] > 32:
            video60 = video
    if video30 or video60:
        return video30 or video60
    else:
        #if not found 720p video return best quality link
        return get_link_video_best_quality(video_data)

def get_link_video_best_quality(video_data):
    """
        video_data['files'] has different links depending on the video quality (resolution and fps)
        this function return best quality link
    """
    data = {}
    for video in video_data['files']:
        if video['quality'] != 'hls':
            aux = int('{}{}'.format(video['height'],int(video['fps'])))
            data[aux] = video
    sort_key = sorted([x for x in data], reverse=True)
    #return best quality link
    return data[sort_key[0]]

def update_create_vimeo_model(edxVideoId, user_id, status, message, course_key_string, url='', vimeo_id=''):
    """
        Create or Update EolVimeoVideo
    """
    data = {
        'status':status,
        'error_description':message
    }
    if url != '':
        data['url_vimeo'] = url
    if vimeo_id != '':
        data['vimeo_video_id'] = vimeo_id
    try:
        course_key = CourseKey.from_string(course_key_string)
        data['course_key'] = course_key
    except InvalidKeyError:
        logger.info('EolVimeo - Invalid CourseKey course_key: {}.'.format(course_key_string))
    logger.info('EolVimeo - Update or Create vimeo model, edxVideoId {}, course: {}, User: {}.'.format(edxVideoId, course_key_string, user_id))
    EolVimeoVideo.objects.update_or_create(
            user_id=user_id,
            edx_video_id=edxVideoId,
            defaults=data)

def duplicate_video(edx_val_id, old_course_key, new_course_key, user=None):
    """
        Duplicate a specific video in another course
    """
    if EolVimeoVideo.objects.filter(edx_video_id=edx_val_id, course_key=old_course_key).exists() and not EolVimeoVideo.objects.filter(edx_video_id=edx_val_id, course_key=new_course_key).exists() :
        vid_vimeo = EolVimeoVideo.objects.get(edx_video_id=edx_val_id, course_key=old_course_key)
        EolVimeoVideo.objects.create(
            edx_video_id = vid_vimeo.edx_video_id,
            user = user if user else vid_vimeo.user,
            vimeo_video_id = vid_vimeo.vimeo_video_id,
            course_key = new_course_key,
            url_vimeo = vid_vimeo.url_vimeo,
            status = vid_vimeo.status,
            error_description = vid_vimeo.error_description
        )
        logger.info('EolVimeo - Duplicate video {} from {} to {}'.format(edx_val_id, old_course_key, new_course_key))
        video = get_video_info(edx_val_id)
        course = {str(new_course_key): None}
        if course not in video['courses']:
            video['courses'] = [course]
            try:
                aux_id = update_video(video)
            except Exception as e:
                logger.exception('EolVimeo - Error to update video path, id_video: {}, exception: {}'.format(edx_val_id, str(e)))
        else:
            logger.info('EOLVimeo - Error duplicate video, edx_video_id: {} with course: {} already exists in edxval'.format(edx_val_id, new_course_key))
    else:
        logger.info('EOLVimeo - Error duplicate video, edx_video_id: {} with course: {} does not exist or already exists in course: {}'.format(edx_val_id, old_course_key, new_course_key))

def duplicate_all_video(old_course_key, new_course_key, user=None):
    """
        Duplicate all video in another course
    """
    old_video_list = EolVimeoVideo.objects.filter(course_key=old_course_key)
    old_video_ids = [x.edx_video_id for x in old_video_list]
    new_video_list = EolVimeoVideo.objects.filter(edx_video_id__in=old_video_ids, course_key=new_course_key)
    new_video_ids = [x.edx_video_id for x in new_video_list]
    for video in old_video_list:
        if video.edx_video_id not in new_video_ids:
            EolVimeoVideo.objects.create(
                edx_video_id = video.edx_video_id,
                user = user if user else video.user,
                vimeo_video_id = video.vimeo_video_id,
                course_key = new_course_key,
                url_vimeo = video.url_vimeo,
                status = video.status,
                error_description = video.error_description
            )
            logger.info('EolVimeo - Duplicate video {} from {} to {}'.format(video.edx_video_id, old_course_key, new_course_key))
