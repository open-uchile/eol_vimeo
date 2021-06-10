# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import six
import json
import os
import math
from django.conf import settings
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
from edxval.models import Video
from edxval.api import update_video, _get_video
from django.core.files.storage import get_storage_class
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

def copy_file(id_file):
    """
        Copy the video file to a temporary directory to get the video path and upload it to vimeo
        return video uri
    """
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, 'video'), 'wb') as local:
                path_video = os.path.join(tmp, 'video')
                video = get_storage().open(id_file)
                shutil.copyfileobj(video, local)
            status = upload(path_video, id_file)
            get_storage().delete(id_file)
            return status
    except Exception:
        #IOError, ClientError
        logger.info('EolVimeo - The id_file does not exists, id_file: {}'.format(id_file))
        return 'Error'

def update_edxval_url(edx_video_id, video_url, file_size, file_name, duration):
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
        "status": "upload_completed"
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
    if not check_credentials():
        logger.info('EolVimeo - Credentials are not defined')
        return False
    client = vimeo.VimeoClient(
        token=settings.EOL_VIMEO_CLIENT_TOKEN,
        key=settings.EOL_VIMEO_CLIENT_ID,
        secret=settings.EOL_VIMEO_CLIENT_SECRET
    )
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
    if not check_credentials():
        logger.info('EolVimeo - Credentials are not defined')
        return {}
    client = vimeo.VimeoClient(
        token=settings.EOL_VIMEO_CLIENT_TOKEN,
        key=settings.EOL_VIMEO_CLIENT_ID,
        secret=settings.EOL_VIMEO_CLIENT_SECRET
    )
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

def move_to_folder(id_video):
    """
        Check if main folder exists in vimeo to move the video there, if not exists, create the folder
        Only check first 100 folders in ascending order
    """
    if not check_credentials():
        logger.info('EolVimeo - Credentials are not defined')
        return False
    client = vimeo.VimeoClient(
        token=settings.EOL_VIMEO_CLIENT_TOKEN,
        key=settings.EOL_VIMEO_CLIENT_ID,
        secret=settings.EOL_VIMEO_CLIENT_SECRET
    )
    next_response = True
    uri_folder = ''
    uri_folder, next_response = get_folders(1, client)
    if uri_folder == 'Error':
        return False
    if uri_folder == '':
        logger.info('EolVimeo - Vimeo folder not found')
        uri_folder = create_folder(client)
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

def create_folder(client):
    """
        Create folder in vimeo.
        return folder uri
    """
    name_folder = settings.EOL_VIMEO_MAIN_FOLDER or "Studio Eol"
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

def get_folders(page, client):
    """
        Get the folders based on the given page.
        100 folders by page
    """
    name_folder = settings.EOL_VIMEO_MAIN_FOLDER or "Studio Eol"
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

def upload(file_name, id_file):
    """
        Upload the video file to Vimeo
    """
    if not check_credentials():
        logger.info('EolVimeo - Credentials are not defined')
        return 'Error'
    client = vimeo.VimeoClient(
        token=settings.EOL_VIMEO_CLIENT_TOKEN,
        key=settings.EOL_VIMEO_CLIENT_ID,
        secret=settings.EOL_VIMEO_CLIENT_SECRET
    )
    try:
        video = _get_video(id_file)
        uri = client.upload(file_name, data={
            'name': video.client_video_id,
            'description': "",
            'privacy': {
                'embed': "whitelist",
                'view': 'disable'
                }
        })
        logger.info('EolVimeo - "{}" has been uploaded to {}'.format(file_name, uri))
        return uri
    except (Exception, vimeo.exceptions.VideoUploadFailure) as e:
        logger.exception('EolVimeo - Error uploading: {}, Exception'.format(file_name, str(e)))
        return 'Error'