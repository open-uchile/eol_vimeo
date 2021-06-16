# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from mock import patch, Mock
from django.test import TestCase, Client
from django.test.client import RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from util.testing import UrlResetMixin
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from common.djangoapps.student.roles import CourseInstructorRole, CourseStaffRole
from common.djangoapps.student.tests.factories import UserFactory, CourseEnrollmentFactory
from capa.tests.response_xml_factory import StringResponseXMLFactory
from lms.djangoapps.courseware.tests.factories import StudentModuleFactory
from opaque_keys.edx.keys import CourseKey
from lms.djangoapps.courseware.courses import get_course_with_access
from six import text_type
from django.test.utils import override_settings
from collections import namedtuple
from six.moves import range
import json
from . import vimeo_utils, vimeo_task
import time
import pytz
from datetime import datetime
from edxval.api import create_video, create_profile

class TestEolVimeo(UrlResetMixin, ModuleStoreTestCase):
    def setUp(self):
        super(TestEolVimeo, self).setUp()
        # create a course
        self.maxDiff = None
        self.course = CourseFactory.create(
            org='mss', course='999', display_name='eol_test_course')

        self.video = {
            "edx_video_id": "123-456-789",
            "client_video_id": "test.mp4",
            "duration": 10,
            "status": 'upload',
            "courses":  [text_type(self.course.id)],
            "created": datetime.now(pytz.utc),
            "encoded_videos": [],
        }
        self.video2 = {
            "edx_video_id": "789-456-123",
            "client_video_id": "test2.mp4",
            "duration": 10,
            "status": 'upload',
            "courses":  [text_type(self.course.id)],
            "created": datetime.now(pytz.utc),
            "encoded_videos": [],
        }
        create_profile("desktop_mp4")
        create_video(self.video)
        create_video(self.video2)

    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.vimeo.VimeoClient.upload")
    @patch("eol_vimeo.vimeo_utils.shutil")
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    def test_upload_video_to_vimeo(self, get_storage, mock_shutil, upload, get, post, put):
        """
            Test upload video to vimeo normal process
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        mock_shutil.configure_mock(copyfileobj=Mock())
        get_data = {'page': 1, 'total': 1, 'data': [{'uri':'/users/112233/projects/12345','name':'test'}]}
        get_data2 = {'name':self.video['client_video_id'], 'duration':self.video['duration'], 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        post_data = {'uri': '/users/112233/projects/995577'}
        
        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data), namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(201, lambda:post_data),]

        upload.return_value = '/videos/123456789'
        
        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'vimeo_encoding', 'message': '', 'vimeo_link':'https://player.vimeo.com/external/1122233344', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.vimeo.VimeoClient.upload")
    @patch("eol_vimeo.vimeo_utils.shutil")
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    def test_upload_video_to_vimeo_multiple_video(self, get_storage, mock_shutil, upload, get, put):
        """
            Test upload video to vimeo normal process with multiple videos
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        mock_shutil.configure_mock(copyfileobj=Mock())
        get_data = {'page': 1, 'total': 1, 'data': [{'uri':'/users/112233/projects/12345','name':'Studio Eol'}]}
        get_data2 = {'name':self.video['client_video_id'], 'duration':self.video['duration'], 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}

        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),
                        namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data), namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),
                        namedtuple("Request", ["status_code", "json"])(200, lambda:get_data), namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]

        upload.return_value = '/videos/123456789'
        
        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''},
                {'edxVideoId': '123', 'status':'upload', 'message': ''},
                {'edxVideoId': self.video2['edx_video_id'], 'status':'upload_completed', 'message': ''},
                {'edxVideoId': '456', 'status':'upload_failed', 'message': ''},
                {'edxVideoId': '789', 'status':'upload_cancelled', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'vimeo_encoding', 'message': '', 'vimeo_link':'https://player.vimeo.com/external/1122233344', 'vimeo_id':'123456789'},
                {'edxVideoId': '123', 'status':'upload', 'message': ''},
                {'edxVideoId': self.video2['edx_video_id'], 'status':'vimeo_encoding', 'message': '', 'vimeo_link':'https://player.vimeo.com/external/1122233344', 'vimeo_id':'123456789'},
                {'edxVideoId': '456', 'status':'upload_failed', 'message': ''},
                {'edxVideoId': '789', 'status':'upload_cancelled', 'message': ''}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.vimeo.VimeoClient.upload")
    @patch("eol_vimeo.vimeo_utils.shutil")
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    def test_upload_video_to_vimeo_folder_exists(self, get_storage, mock_shutil, upload, get, put):
        """
            Test upload video to vimeo normal process when folders in vimeo exists
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        mock_shutil.configure_mock(copyfileobj=Mock())
        get_data = {'page': 1, 'total': 1, 'data': [{'uri':'/users/112233/projects/12345','name':'Studio Eol'}]}
        get_data2 = {'name':self.video['client_video_id'], 'duration':self.video['duration'], 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}

        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data), namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]

        upload.return_value = '/videos/123456789'
        
        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'vimeo_encoding', 'message': '', 'vimeo_link':'https://player.vimeo.com/external/1122233344', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch("eol_vimeo.vimeo_utils.update_video")
    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.vimeo.VimeoClient.upload")
    @patch("eol_vimeo.vimeo_utils.shutil")
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    def test_upload_video_to_vimeo_fail_patch(self, get_storage, mock_shutil, upload, get, post, put, mock_update_video):
        """
            Test upload video to vimeo when fail update in edxval model
        """
        mock_update_video.side_effect = Exception()
        get_storage.configure_mock(open=Mock(), delete=Mock())
        mock_shutil.configure_mock(copyfileobj=Mock())
        get_data = {'page': 1, 'total': 1, 'data': [{'uri':'/users/112233/projects/12345','name':'test'}]}
        get_data2 = {'name':self.video['client_video_id'], 'duration':self.video['duration'], 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        post_data = {'uri': '/users/112233/projects/995577'}
        
        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data), namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(201, lambda:post_data),]

        upload.return_value = '/videos/123456789'
        
        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_failed', 'message': 'No se pudo agregar el path vimeo del video al video en plataforma(error update_video in edxval.api). ', 'vimeo_link':'https://player.vimeo.com/external/1122233344', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.vimeo.VimeoClient.upload")
    @patch("eol_vimeo.vimeo_utils.shutil")
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    def test_upload_video_to_vimeo_fail_get_video(self, get_storage, mock_shutil, upload, get, post, put):
        """
            Test upload video to vimeo when fail to get video in vimeo
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        mock_shutil.configure_mock(copyfileobj=Mock())
        get_data = {'page': 1, 'total': 1, 'data': [{'uri':'/users/112233/projects/12345','name':'test'}]}
        get_data2 = {'error': "The requested video couldn't be found."}
        post_data = {'uri': '/users/112233/projects/995577'}
        
        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data), namedtuple("Request", ["status_code", "json"])(404, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(201, lambda:post_data),]

        upload.return_value = '/videos/123456789'
        
        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_failed', 'message': 'No se pudo obtener el video en Vimeo. ', 'vimeo_link':'', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.vimeo.VimeoClient.upload")
    @patch("eol_vimeo.vimeo_utils.shutil")
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    def test_upload_video_to_vimeo_fail_get_video_no_files(self, get_storage, mock_shutil, upload, get, post, put):
        """
            Test upload video to vimeo when video in vimeo dont have files
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        mock_shutil.configure_mock(copyfileobj=Mock())
        get_data = {'page': 1, 'total': 1, 'data': [{'uri':'/users/112233/projects/12345','name':'test'}]}
        get_data2 = {'name':self.video['client_video_id'], 'duration':self.video['duration'], 'files': []}
        post_data = {'uri': '/users/112233/projects/995577'}
        
        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data), namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(201, lambda:post_data),]

        upload.return_value = '/videos/123456789'
        
        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_failed', 'message': 'No se pudo obtener el video en Vimeo. ', 'vimeo_link':'', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.vimeo.VimeoClient.upload")
    @patch("eol_vimeo.vimeo_utils.shutil")
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    def test_upload_video_to_vimeo_fail_get_video_basic_user(self, get_storage, mock_shutil, upload, get, post, put):
        """
            Test upload video to vimeo when user vimeo only have basic plan
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        mock_shutil.configure_mock(copyfileobj=Mock())
        get_data = {'page': 1, 'total': 1, 'data': [{'uri':'/users/112233/projects/12345','name':'test'}]}
        get_data2 = {'name':self.video['client_video_id'], 'duration':self.video['duration']}
        post_data = {'uri': '/users/112233/projects/995577'}
        
        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data), namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(201, lambda:post_data),]

        upload.return_value = '/videos/123456789'
        
        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_failed', 'message': 'No se pudo obtener el video en Vimeo. ', 'vimeo_link':'', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.vimeo.VimeoClient.upload")
    @patch("eol_vimeo.vimeo_utils.shutil")
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    def test_upload_video_to_vimeo_fail_move_to_folder_get_folders(self, get_storage, mock_shutil, upload, get, put):
        """
            Test upload video to vimeo when fail get folders in vimeo
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        mock_shutil.configure_mock(copyfileobj=Mock())
        get_data = {'error': 'Something strange occurred. Please contact the app owners.', 'link': None, 'developer_message': 'The credentials provided are invalid.', 'error_code': 8000}
        get_data2 = {'name':self.video['client_video_id'], 'duration':self.video['duration'], 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}

        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(401, lambda:get_data), namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]

        upload.return_value = '/videos/123456789'

        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'vimeo_encoding', 'message': 'No se pudo mover el video a la carpeta principal en Vimeo. ', 'vimeo_link':'https://player.vimeo.com/external/1122233344', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.vimeo.VimeoClient.upload")
    @patch("eol_vimeo.vimeo_utils.shutil")
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    def test_upload_video_to_vimeo_fail_move_to_folder_create_folder(self, get_storage, mock_shutil, upload, get, post, put):
        """
            Test upload video to vimeo when fail create folder in vimeo
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        mock_shutil.configure_mock(copyfileobj=Mock())
        get_data = {'page': 1, 'total': 1, 'data': [{'uri':'/users/112233/projects/12345','name':'test'}]}
        get_data2 = {'name':self.video['client_video_id'], 'duration':self.video['duration'], 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        post_data = {'error': 'Something strange occurred. Please contact the app owners.', 'link': None, 'developer_message': 'The credentials provided are invalid.', 'error_code': 8000}
        
        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data), namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(401, lambda:post_data),]

        upload.return_value = '/videos/123456789'
        
        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'vimeo_encoding', 'message': 'No se pudo mover el video a la carpeta principal en Vimeo. ', 'vimeo_link':'https://player.vimeo.com/external/1122233344', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.vimeo.VimeoClient.upload")
    @patch("eol_vimeo.vimeo_utils.shutil")
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    def test_upload_video_to_vimeo_fail_move_to_folder_move_video(self, get_storage, mock_shutil, upload, get, post, put):
        """
            Test upload video to vimeo when fail move video to folder in vimeo
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        mock_shutil.configure_mock(copyfileobj=Mock())
        get_data = {'page': 1, 'total': 1, 'data': [{'uri':'/users/112233/projects/12345','name':'test'}]}
        get_data2 = {'name':self.video['client_video_id'], 'duration':self.video['duration'], 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        post_data = {'uri': '/users/112233/projects/995577'}
        put_data = {'error': 'Your access token does not have the "interact" scope'}
        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code", "json"])(403, lambda:put_data),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data), namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(201, lambda:post_data),]

        upload.return_value = '/videos/123456789'
        
        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'vimeo_encoding', 'message': 'No se pudo mover el video a la carpeta principal en Vimeo. ', 'vimeo_link':'https://player.vimeo.com/external/1122233344', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.vimeo.VimeoClient.upload")
    @patch("eol_vimeo.vimeo_utils.shutil")
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    def test_upload_video_to_vimeo_fail_add_domain(self, get_storage, mock_shutil, upload, get, post, put):
        """
            Test upload video to vimeo when fail add domain to video in vimeo
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        mock_shutil.configure_mock(copyfileobj=Mock())
        get_data = {'page': 1, 'total': 1, 'data': [{'uri':'/users/112233/projects/12345','name':'test'}]}
        get_data2 = {'name':self.video['client_video_id'], 'duration':self.video['duration'], 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        post_data = {'uri': '/users/112233/projects/995577'}
        put_data = {'error': 'Something strange occurred. Please contact the app owners.', 'link': None, 'developer_message': 'The credentials provided are invalid.', 'error_code': 8000}
        put.side_effect = [namedtuple("Request", ["status_code", "json"])(403, lambda:put_data),namedtuple("Request", ["status_code", "json"])(403, lambda:put_data),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data), namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "json"])(201, lambda:post_data),]
        upload.return_value = '/videos/123456789'
        
        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'vimeo_encoding', 'message': 'No se pudo agregar los dominios al video en Vimeo. ', 'vimeo_link':'https://player.vimeo.com/external/1122233344', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch("eol_vimeo.vimeo_utils.copy_file")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_upload_video_to_vimeo_fail_upload(self, copy_file):
        """
            Test upload video to vimeo when fail storage_class 
        """
        copy_file.return_value = 'Error'

        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_failed', 'message': 'No se pudo subir el video a Vimeo. ', 'vimeo_link':'', 'vimeo_id':''}]
        self.assertEqual(response, data2)
    
    @patch("eol_vimeo.vimeo_utils.vimeo.VimeoClient.upload")
    @patch("eol_vimeo.vimeo_utils.shutil")
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_upload_video_to_vimeo_fail_upload_2(self, get_storage, mock_shutil, upload):
        """
            Test upload video to vimeo when upload video to vimeo
        """
        upload.side_effect = Exception()
        get_storage.configure_mock(open=Mock(), delete=Mock())
        mock_shutil.configure_mock(copyfileobj=Mock())

        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_failed', 'message': 'No se pudo subir el video a Vimeo. ', 'vimeo_link':'', 'vimeo_id':''}]
        self.assertEqual(response, data2)

    @patch("eol_vimeo.vimeo_utils.shutil")
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='')
    def test_upload_video_to_vimeo_no_credentials(self, get_storage, mock_shutil):
        """
            Test upload video to vimeo when credentials are not defined
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        mock_shutil.configure_mock(copyfileobj=Mock())

        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_failed', 'message': 'No se pudo subir el video a Vimeo. ', 'vimeo_link':'', 'vimeo_id':''}]
        self.assertEqual(response, data2)