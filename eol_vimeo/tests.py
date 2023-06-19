# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from mock import patch, Mock
from django.test import TestCase, Client
from django.test.client import RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from common.djangoapps.util.testing import UrlResetMixin
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from common.djangoapps.student.roles import CourseInstructorRole, CourseStaffRole
from common.djangoapps.student.tests.factories import UserFactory, CourseEnrollmentFactory
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from capa.tests.response_xml_factory import StringResponseXMLFactory
from lms.djangoapps.courseware.tests.factories import StudentModuleFactory
from opaque_keys.edx.keys import CourseKey
from lms.djangoapps.courseware.courses import get_course_with_access
from six import text_type
from django.test.utils import override_settings
from django.conf import settings
from collections import namedtuple
from six.moves import range
import json
from . import vimeo_utils, vimeo_task
import time
import pytz
import datetime
import urllib.parse
from .models import EolVimeoVideo
from edxval.api import create_video, create_profile, get_video_info

class TestEolVimeo(UrlResetMixin, ModuleStoreTestCase):
    def setUp(self):
        super(TestEolVimeo, self).setUp()
        # create a course
        self.maxDiff = None
        self.course = CourseFactory.create(
            org='mss', course='999', display_name='eol_test_course')
        self.course2 = CourseFactory.create(
            org='mss', course='222', display_name='eol_test_course2')
        self.video = {
            "edx_video_id": "123-456-789",
            "client_video_id": "test.mp4",
            "duration": 10,
            "status": 'vimeo_upload',
            "courses":  [text_type(self.course.id)],
            "created": datetime.datetime.now(pytz.utc),
            "encoded_videos": [],
        }
        self.video2 = {
            "edx_video_id": "789-456-123",
            "client_video_id": "test2.mp4",
            "duration": 10,
            "status": 'vimeo_upload',
            "courses":  [text_type(self.course.id)],
            "created": datetime.datetime.now(pytz.utc),
            "encoded_videos": [],
        }
        create_profile("desktop_mp4")
        create_video(self.video)
        create_video(self.video2)
        with patch('common.djangoapps.student.models.cc.User.save'):
            # staff user
            self.user = UserFactory(
                username='testuser2',
                password='12345',
                email='student2@edx.org',
                is_staff=True)
            self.user2 = UserFactory(
                username='testuser3',
                password='12345',
                email='student3@edx.org',
                is_staff=True)

    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    @override_settings(EOL_VIMEO_MAIN_FOLDER='12345')
    def test_upload_video_to_vimeo(self, get_storage, get, post, put):
        """
            Test upload video to vimeo normal process
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        get_storage.configure_mock(open=Mock(), delete=Mock())
        get_data2 = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'in_progress'},'duration':self.video['duration'], 'upload': {'status': 'in_progress'}, 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        post_data = {'upload': {'status': 'in_progress'}, 'uri': '/videos/123456789'}
        post_data2 = {'uri': '/users/112233/projects/995577'}

        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "text"])(201, json.dumps(post_data)), namedtuple("Request", ["status_code", "json"])(201, lambda:post_data2),]

        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data, settings.EOL_VIMEO_MAIN_FOLDER, 'https://test.test.ts', self.course.id)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'vimeo_upload', 'message': '', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    @override_settings(EOL_VIMEO_MAIN_FOLDER='12345')
    def test_upload_video_to_vimeo_multiple_video(self, get_storage, get, post, put):
        """
            Test upload video to vimeo normal process with multiple videos
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        EolVimeoVideo.objects.create(
            edx_video_id = self.video2["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        get_storage.configure_mock(open=Mock(), delete=Mock())
        get_data2 = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'in_progress'}, 'duration':self.video['duration'], 'upload': {'status': 'in_progress'}, 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        post_data = {'upload': {'status': 'in_progress'}, 'uri': '/videos/123456789'}

        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),
                        namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2), namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "text"])(201, json.dumps(post_data)), namedtuple("Request", ["status_code", "text"])(201, json.dumps(post_data)),]
        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''},
                {'edxVideoId': '123', 'status':'upload', 'message': ''},
                {'edxVideoId': self.video2['edx_video_id'], 'status':'upload_completed', 'message': ''},
                {'edxVideoId': '456', 'status':'upload_failed', 'message': ''},
                {'edxVideoId': '789', 'status':'upload_cancelled', 'message': ''}]
        response = vimeo_task.upload_vimeo(data, settings.EOL_VIMEO_MAIN_FOLDER, 'https://test.test.ts', self.course.id)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'vimeo_upload', 'message': '', 'vimeo_id':'123456789'},
                {'edxVideoId': '123', 'status':'upload', 'message': ''},
                {'edxVideoId': self.video2['edx_video_id'], 'status':'vimeo_upload', 'message': '', 'vimeo_id':'123456789'},
                {'edxVideoId': '456', 'status':'upload_failed', 'message': ''},
                {'edxVideoId': '789', 'status':'upload_cancelled', 'message': ''}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    @override_settings(EOL_VIMEO_MAIN_FOLDER='12345')
    def test_upload_video_to_vimeo_folder_exists(self, get_storage, get, post, put):
        """
            Test upload video to vimeo normal process when folders in vimeo exists
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        get_storage.configure_mock(open=Mock(), delete=Mock())
        get_data2 = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'in_progress'}, 'duration':self.video['duration'], 'upload': {'status': 'in_progress'}, 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        post_data = {'upload': {'status': 'in_progress'}, 'uri': '/videos/123456789'}
        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "text"])(201, json.dumps(post_data)),]

        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data, settings.EOL_VIMEO_MAIN_FOLDER, 'https://test.test.ts', self.course.id)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'vimeo_upload', 'message': '', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    @override_settings(EOL_VIMEO_MAIN_FOLDER='12345')
    def test_upload_video_to_vimeo_fail_get_video(self, get_storage, get, post, put):
        """
            Test upload video to vimeo when fail to get video in vimeo
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        get_storage.configure_mock(open=Mock(), delete=Mock())
        get_data2 = {'error': "The requested video couldn't be found."}
        post_data = {'upload': {'status': 'in_progress'}, 'uri': '/videos/123456789'}
        post_data2 = {'uri': '/users/112233/projects/995577'}

        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(404, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "text"])(201, json.dumps(post_data)), namedtuple("Request", ["status_code", "json"])(201, lambda:post_data2),]

        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data, settings.EOL_VIMEO_MAIN_FOLDER, 'https://test.test.ts', self.course.id)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_failed', 'message': 'Video no se subio correctamente a Vimeo. ', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    @override_settings(EOL_VIMEO_MAIN_FOLDER='12345')
    def test_upload_video_to_vimeo_fail_move_to_folder_move_video(self, get_storage, get, post, put):
        """
            Test upload video to vimeo when fail move video to folder in vimeo
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        get_storage.configure_mock(open=Mock(), delete=Mock())
        get_data2 = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'in_progress'}, 'duration':self.video['duration'], 'upload': {'status': 'in_progress'}, 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        post_data = {'upload': {'status': 'in_progress'}, 'uri': '/videos/123456789'}
        post_data2 = {'uri': '/users/112233/projects/995577'}
        put_data = {'error': 'Your access token does not have the "interact" scope'}
        put.side_effect = [namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code"])(204),namedtuple("Request", ["status_code", "json"])(403, lambda:put_data),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "text"])(201, json.dumps(post_data)), namedtuple("Request", ["status_code", "json"])(201, lambda:post_data2),]

        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data, settings.EOL_VIMEO_MAIN_FOLDER, 'https://test.test.ts', self.course.id)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'vimeo_upload', 'message': 'No se pudo mover el video a la carpeta principal en Vimeo. ', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch('requests.put')
    @patch('requests.post')
    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    @override_settings(EOL_VIMEO_DOMAINS=['test.cl', 'studio.test.cl'])
    @override_settings(EOL_VIMEO_MAIN_FOLDER='12345')
    def test_upload_video_to_vimeo_fail_add_domain(self, get_storage, get, post, put):
        """
            Test upload video to vimeo when fail add domain to video in vimeo
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        get_storage.configure_mock(open=Mock(), delete=Mock())
        get_data2 = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'in_progress'}, 'duration':self.video['duration'], 'upload': {'status': 'in_progress'}, 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        post_data = {'upload': {'status': 'in_progress'}, 'uri': '/videos/123456789'}
        post_data2 = {'uri': '/users/112233/projects/995577'}
        put_data = {'error': 'Something strange occurred. Please contact the app owners.', 'link': None, 'developer_message': 'The credentials provided are invalid.', 'error_code': 8000}
        put.side_effect = [namedtuple("Request", ["status_code", "json"])(403, lambda:put_data),namedtuple("Request", ["status_code", "json"])(403, lambda:put_data),namedtuple("Request", ["status_code"])(204),]
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        post.side_effect = [namedtuple("Request", ["status_code", "text"])(201, json.dumps(post_data)), namedtuple("Request", ["status_code", "json"])(201, lambda:post_data2),]
        
        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data, settings.EOL_VIMEO_MAIN_FOLDER, 'https://test.test.ts', self.course.id)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'vimeo_upload', 'message': 'No se pudo agregar los dominios al video en Vimeo. ', 'vimeo_id':'123456789'}]
        self.assertEqual(response, data2)

    @patch('requests.post')
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_upload_video_to_vimeo_fail_upload(self, post):
        """
            Test upload video to vimeo when fail storage_class 
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        post_data = {'upload': {'status': 'error'}, 'uri': '/videos/123456789'}
        post.side_effect = [namedtuple("Request", ["status_code", "text"])(201, json.dumps(post_data)),]

        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data, settings.EOL_VIMEO_MAIN_FOLDER, 'https://test.test.ts', self.course.id)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_failed', 'message': 'No se pudo subir el video a Vimeo. ', 'vimeo_id':''}]
        self.assertEqual(response, data2)

    @patch('requests.post')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_upload_video_to_vimeo_fail_upload_2(self, get_storage, post):
        """
            Test upload video to vimeo when upload video to vimeo
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        get_storage.configure_mock(open=Mock(), delete=Mock())
        post.side_effect = [namedtuple("Request", ["status_code", "text"])(400, 'error'),]

        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data, settings.EOL_VIMEO_MAIN_FOLDER, 'https://test.test.ts', self.course.id)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_failed', 'message': 'No se pudo subir el video a Vimeo. ', 'vimeo_id':''}]
        self.assertEqual(response, data2)

    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='')
    def test_upload_video_to_vimeo_no_credentials(self, get_storage):
        """
            Test upload video to vimeo when credentials are not defined
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        get_storage.configure_mock(open=Mock(), delete=Mock())
        data = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_completed', 'message': ''}]
        response = vimeo_task.upload_vimeo(data, settings.EOL_VIMEO_MAIN_FOLDER, 'https://test.test.ts', self.course.id)
        data2 = [{'edxVideoId': self.video['edx_video_id'], 'status':'upload_failed', 'message': 'No se pudo subir el video a Vimeo. ', 'vimeo_id':''}]
        self.assertEqual(response, data2)

    def test_duplicate_video_normal_process(self):
        """
            Test duplicate a specific video normal process
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = 'url_video_vimeo',
            status = 'upload_completed',
            error_description = ''
        )
        self.assertEqual(len(EolVimeoVideo.objects.all()), 1)
        video = get_video_info(self.video["edx_video_id"])
        self.assertTrue({str(self.course2.id): None} not in video['courses'])
        vimeo_utils.duplicate_video(self.video["edx_video_id"], self.course.id, self.course2.id, self.user2)
        video = get_video_info(self.video["edx_video_id"])
        self.assertTrue({str(self.course2.id): None} in video['courses'])
        self.assertEqual(len(EolVimeoVideo.objects.all()), 2)
        eolvimeo_model = EolVimeoVideo.objects.get(course_key=self.course2.id, edx_video_id=self.video["edx_video_id"])
        self.assertEqual(eolvimeo_model.user, self.user2)

    def test_duplicate_video_normal_process_without_user(self):
        """
            Test duplicate a specific video normal process without user
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = 'url_video_vimeo',
            status = 'upload_completed',
            error_description = ''
        )
        self.assertEqual(len(EolVimeoVideo.objects.all()), 1)
        video = get_video_info(self.video["edx_video_id"])
        self.assertTrue({str(self.course2.id): None} not in video['courses'])
        vimeo_utils.duplicate_video(self.video["edx_video_id"], self.course.id, self.course2.id)
        video = get_video_info(self.video["edx_video_id"])
        self.assertTrue({str(self.course2.id): None} in video['courses'])
        self.assertEqual(len(EolVimeoVideo.objects.all()), 2)
        eolvimeo_model = EolVimeoVideo.objects.get(course_key=self.course2.id, edx_video_id=self.video["edx_video_id"])
        self.assertEqual(eolvimeo_model.user, self.user)

    def test_duplicate_video_normal_process_no_model(self):
        """
            Test duplicate a specific video, video no exists in eolvimeo model
        """
        self.assertEqual(len(EolVimeoVideo.objects.all()), 0)
        video = get_video_info(self.video["edx_video_id"])
        self.assertTrue({str(self.course2.id): None} not in video['courses'])
        vimeo_utils.duplicate_video(self.video["edx_video_id"], self.course.id, self.course2.id)
        video = get_video_info(self.video["edx_video_id"])
        self.assertFalse({str(self.course2.id): None} in video['courses'])
        self.assertEqual(len(EolVimeoVideo.objects.all()), 0)

    def test_duplicate_video_normal_process_already_exists(self):
        """
            Test duplicate a specific video video already exists in eolvimeo model
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = 'url_video_vimeo',
            status = 'upload_completed',
            error_description = ''
        )
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course2.id,
            url_vimeo = 'url_video_vimeo',
            status = 'upload_completed',
            error_description = ''
        )
        self.assertEqual(len(EolVimeoVideo.objects.all()), 2)
        video = get_video_info(self.video["edx_video_id"])
        self.assertTrue({str(self.course2.id): None} not in video['courses'])
        vimeo_utils.duplicate_video(self.video["edx_video_id"], self.course.id, self.course2.id)
        video = get_video_info(self.video["edx_video_id"])
        self.assertFalse({str(self.course2.id): None} in video['courses'])
        self.assertEqual(len(EolVimeoVideo.objects.all()), 2)

    @patch("eol_vimeo.vimeo_utils.update_video")
    def test_duplicate_video_fail_update_edxval(self, mock_update_video):
        """
            Test duplicate a specific video, fail update video in edxval
        """
        mock_update_video.side_effect = Exception()
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = 'url_video_vimeo',
            status = 'upload_completed',
            error_description = ''
        )
        self.assertEqual(len(EolVimeoVideo.objects.all()), 1)
        video = get_video_info(self.video["edx_video_id"])
        self.assertTrue({str(self.course2.id): None} not in video['courses'])
        vimeo_utils.duplicate_video(self.video["edx_video_id"], self.course.id, self.course2.id)
        self.assertFalse({str(self.course2.id): None} in video['courses'])
        self.assertEqual(len(EolVimeoVideo.objects.all()), 2)
        eolvimeo_model = EolVimeoVideo.objects.get(course_key=self.course2.id, edx_video_id=self.video["edx_video_id"])
        self.assertEqual(eolvimeo_model.user, self.user)

    def test_duplicate_all_video_normal_process(self):
        """
            Test duplicate all video vimeo normal process
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = 'url_video_vimeo',
            status = 'upload_completed',
            error_description = ''
        )
        EolVimeoVideo.objects.create(
            edx_video_id = self.video2["edx_video_id"],
            user =self.user,
            vimeo_video_id = '9922334455',
            course_key = self.course.id,
            url_vimeo = 'url_video_vimeo2',
            status = 'upload_completed',
            error_description = ''
        )
        self.assertEqual(len(EolVimeoVideo.objects.all()), 2)

        vimeo_utils.duplicate_all_video(self.course.id, self.course2.id)
        self.assertEqual(len(EolVimeoVideo.objects.all()), 4)
        self.assertEqual(len(EolVimeoVideo.objects.filter(course_key=self.course2.id)), 2)

    def test_duplicate_all_video_normal_process_with_user(self):
        """
            Test duplicate all video vimeo normal process
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = 'url_video_vimeo',
            status = 'upload_completed',
            error_description = ''
        )
        self.assertEqual(len(EolVimeoVideo.objects.all()), 1)

        vimeo_utils.duplicate_all_video(self.course.id, self.course2.id, self.user2)
        self.assertEqual(len(EolVimeoVideo.objects.all()), 2)
        eolvimeo_model = EolVimeoVideo.objects.get(course_key=self.course2.id, edx_video_id=self.video["edx_video_id"])
        self.assertEqual(eolvimeo_model.user, self.user2)

    def test_duplicate_all_video_exists_video(self):
        """
            Test duplicate all video vimeo, when videos already exists in eolvimeo model
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = 'url_video_vimeo',
            status = 'upload_completed',
            error_description = ''
        )
        EolVimeoVideo.objects.create(
            edx_video_id = self.video2["edx_video_id"],
            user =self.user,
            vimeo_video_id = '9922334455',
            course_key = self.course.id,
            url_vimeo = 'url_video_vimeo2',
            status = 'upload_completed',
            error_description = ''
        )
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course2.id,
            url_vimeo = 'url_video_vimeo',
            status = 'upload_completed',
            error_description = ''
        )
        EolVimeoVideo.objects.create(
            edx_video_id = self.video2["edx_video_id"],
            user =self.user,
            vimeo_video_id = '9922334455',
            course_key = self.course2.id,
            url_vimeo = 'url_video_vimeo2',
            status = 'upload_completed',
            error_description = ''
        )
        self.assertEqual(len(EolVimeoVideo.objects.all()), 4)

        vimeo_utils.duplicate_all_video(self.course.id, self.course2.id)
        self.assertEqual(len(EolVimeoVideo.objects.all()), 4)
        self.assertEqual(len(EolVimeoVideo.objects.filter(course_key=self.course2.id)), 2)

    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo(self, get_storage, get):
        """
            Test update_video_vimeo normal process
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = '',
            expiry_at=datetime.datetime.utcnow()
        )
        EolVimeoVideo.objects.create(
            edx_video_id = self.video2["edx_video_id"],
            user =self.user,
            vimeo_video_id = '9922334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_upload',
            error_description = '',
            expiry_at=datetime.datetime.utcnow()
        )
        get_storage.configure_mock(open=Mock(), delete=Mock())
        get_data = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'complete'}, 'duration':self.video['duration'], 'upload': {'status': 'complete'}, 'files': [{'quality': 'hd', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'HD 720p', 'size_short': ''}]}
        get_data2 = {'name':self.video2['client_video_id'], 'status':'available', 'transcode': {'status': 'complete'}, 'duration':self.video2['duration'], 'upload': {'status': 'complete'}, 'files': [{'quality': 'hd', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/9922233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'HD 720p', 'size_short': ''}]}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        vimeo_utils.update_video_vimeo(str(self.course.id))
        eolvimeo1 = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        eolvimeo2 = EolVimeoVideo.objects.get(edx_video_id=self.video2["edx_video_id"])
        self.assertEqual(eolvimeo1.status, 'upload_completed')
        self.assertEqual(eolvimeo1.url_vimeo, get_data['files'][0]['link'])
        self.assertEqual(eolvimeo2.status, 'upload_completed')
        self.assertEqual(eolvimeo2.url_vimeo, get_data2['files'][0]['link'])

    def test_update_video_vimeo_no_credentials(self):
        """
            Test update_video_vimeo when credentials are not defined
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        EolVimeoVideo.objects.create(
            edx_video_id = self.video2["edx_video_id"],
            user =self.user,
            vimeo_video_id = '9922334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_upload',
            error_description = ''
        )
        vimeo_utils.update_video_vimeo(str(self.course.id))
        eolvimeo1 = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        eolvimeo2 = EolVimeoVideo.objects.get(edx_video_id=self.video2["edx_video_id"])
        self.assertEqual(eolvimeo1.status, 'vimeo_encoding')
        self.assertEqual(eolvimeo1.url_vimeo, '')
        self.assertEqual(eolvimeo2.status, 'vimeo_upload')
        self.assertEqual(eolvimeo2.url_vimeo, '')

    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_no_course(self, get_storage, get):
        """
            Test update_video_vimeo normal process when course is None
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = '',
            expiry_at=datetime.datetime.utcnow()
        )
        EolVimeoVideo.objects.create(
            edx_video_id = self.video2["edx_video_id"],
            user =self.user,
            vimeo_video_id = '9922334455',
            course_key = CourseKey.from_string('course-v1:eol+Test101+2021'),
            url_vimeo = '',
            status = 'vimeo_upload',
            error_description = '',
            expiry_at=datetime.datetime.utcnow()
        )
        get_storage.configure_mock(open=Mock(), delete=Mock())
        get_data = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'complete'}, 'duration':self.video['duration'], 'upload': {'status': 'complete'}, 'files': [{'quality': 'hd', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'HD 720p', 'size_short': ''}]}
        get_data2 = {'name':self.video2['client_video_id'], 'status':'available', 'transcode': {'status': 'complete'},  'duration':self.video2['duration'], 'upload': {'status': 'complete'}, 'files': [{'quality': 'hd', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/9922233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'HD 720p', 'size_short': ''}]}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),namedtuple("Request", ["status_code", "json"])(200, lambda:get_data2),]
        vimeo_utils.update_video_vimeo()
        eolvimeo1 = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        eolvimeo2 = EolVimeoVideo.objects.get(edx_video_id=self.video2["edx_video_id"])
        self.assertEqual(eolvimeo1.status, 'upload_completed')
        self.assertEqual(eolvimeo1.url_vimeo, get_data['files'][0]['link'])
        self.assertEqual(eolvimeo2.status, 'upload_completed')
        self.assertEqual(eolvimeo2.url_vimeo, get_data2['files'][0]['link'])

    @patch('requests.get')
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_fail_get_video(self, get):
        """
            Test update_video_vimeo when fail to get video in vimeo
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        get_data = {'error': "The requested video couldn't be found."}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(404, lambda:get_data),]
        vimeo_utils.update_video_vimeo(str(self.course.id))
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        video = get_video_info(self.video["edx_video_id"])
        self.assertEqual(video['status'], 'vimeo_not_found')
        self.assertEqual(eolvimeo.status, 'vimeo_not_found')

    @patch('requests.get')
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_upload_error(self, get):
        """
            Test update_video_vimeo when upload video failed
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        get_data = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'complete'}, 'duration':self.video['duration'], 'upload': {'status': 'error'}, 'files': []}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),]
        vimeo_utils.update_video_vimeo()
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        video = get_video_info(self.video["edx_video_id"])
        self.assertEqual(video['status'], 'upload_failed')
        self.assertEqual(eolvimeo.status, 'upload_failed')

    @patch('requests.get')
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_upload_error_status(self, get):
        """
            Test update_video_vimeo when upload video failed
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        get_data = {'name':self.video['client_video_id'], 'status':'uploading_error', 'transcode': {'status': 'complete'}, 'duration':self.video['duration'], 'upload': {'status': 'complete'}, 'files': [{'quality': 'hd', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),]
        vimeo_utils.update_video_vimeo()
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        video = get_video_info(self.video["edx_video_id"])
        self.assertEqual(video['status'], 'upload_failed')
        self.assertEqual(eolvimeo.status, 'upload_failed')
        self.assertEqual(eolvimeo.error_description, 'Video no se subio correctamente a Vimeo. status=uploading_error')

    @patch('requests.get')
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_upload_error_transcode(self, get):
        """
            Test update_video_vimeo when transcode video failed
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_encoding',
            error_description = ''
        )
        get_data = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'error'}, 'duration':self.video['duration'], 'upload': {'status': 'complete'}, 'files': [{'quality': 'hd', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),]
        vimeo_utils.update_video_vimeo()
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        video = get_video_info(self.video["edx_video_id"])
        self.assertEqual(video['status'], 'upload_failed')
        self.assertEqual(eolvimeo.status, 'upload_failed')
        self.assertEqual(eolvimeo.error_description, 'Video no fue procesado correctamente en Vimeo. ')

    @patch('requests.get')
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_upload_transcode_in_progress(self, get):
        """
            Test update_video_vimeo when video is still encoding in vimeo
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_upload',
            error_description = ''
        )
        get_data = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'in_progress'}, 'duration':self.video['duration'], 'upload': {'status': 'complete'}, 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),]
        vimeo_utils.update_video_vimeo()
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        video = get_video_info(self.video["edx_video_id"])
        self.assertEqual(video['status'], 'vimeo_encoding')
        self.assertEqual(eolvimeo.status, 'vimeo_encoding')
        self.assertEqual(eolvimeo.error_description, 'Vimeo todavia esta procesando el video.')

    @patch('requests.get')
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_fail_get_files(self, get):
        """
            Test update_video_vimeo when video files is empty
        """
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_upload',
            error_description = ''
        )
        get_data = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'complete'}, 'duration':self.video['duration'], 'upload': {'status': 'complete'}, 'files': []}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),]
        vimeo_utils.update_video_vimeo()
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        video = get_video_info(self.video["edx_video_id"])
        self.assertEqual(video['status'], 'vimeo_upload')
        self.assertEqual(eolvimeo.status, 'vimeo_upload')
        self.assertEqual(eolvimeo.error_description, 'No se pudo obtener los links del video en Vimeo. ')

    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_vimeo_processing(self, get_storage, get):
        """
            Test update_video_vimeo when is still processing in vimeo
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_upload',
            error_description = ''
        )
        get_data = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'in_progress'}, 'duration':self.video['duration'], 'upload': {'status': 'complete'}, 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),]
        vimeo_utils.update_video_vimeo()
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        video = get_video_info(self.video["edx_video_id"])
        self.assertEqual(video['status'], 'vimeo_encoding')
        self.assertEqual(eolvimeo.status, 'vimeo_encoding')
        self.assertEqual(eolvimeo.error_description, 'Vimeo todavia esta procesando el video.')

    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_vimeo_uploading(self, get_storage, get):
        """
            Test update_video_vimeo when video is still uploading in vimeo
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_upload',
            error_description = ''
        )
        get_data = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'in_progress'}, 'duration':self.video['duration'], 'upload': {'status': 'in_progress'}, 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),]
        vimeo_utils.update_video_vimeo()
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        video = get_video_info(self.video["edx_video_id"])
        self.assertEqual(video['status'], 'vimeo_upload')
        self.assertEqual(eolvimeo.status, 'vimeo_upload')
        self.assertEqual(eolvimeo.error_description, 'Vimeo todavia esta subiendo el video. ')

    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_vimeo_transcode_expiry(self, get_storage, get):
        """
            Test update_video_vimeo when the video takes more than 24 hours processing
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_upload',
            error_description = '',
            expiry_at=(datetime.datetime.utcnow() - datetime.timedelta(hours=25))
        )
        get_data = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'complete'}, 'duration':self.video['duration'], 'upload': {'status': 'complete'}, 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'SD 640p', 'size_short': ''}]}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),]
        vimeo_utils.update_video_vimeo()
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        video = get_video_info(self.video["edx_video_id"])
        self.assertEqual(video['status'], 'upload_completed')
        self.assertEqual(eolvimeo.status, 'upload_completed')
        self.assertEqual(eolvimeo.error_description, 'upload_completed, Lleva mas de 24 hrs procesando o video no tiene formato HD')

    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_vimeo_transcode_expiry_2(self, get_storage, get):
        """
            Test update_video_vimeo when the video takes more than 24 hours processing and only have hls quality
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_upload',
            error_description = '',
            expiry_at=(datetime.datetime.utcnow() - datetime.timedelta(hours=25))
        )
        get_data = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'complete'}, 'duration':self.video['duration'], 'upload': {'status': 'complete'}, 'files': [{'quality': 'hls', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'SD 640p', 'size_short': ''}]}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),]
        vimeo_utils.update_video_vimeo()
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        video = get_video_info(self.video["edx_video_id"])
        self.assertEqual(video['status'], 'upload_failed')
        self.assertEqual(eolvimeo.status, 'upload_failed')
        self.assertEqual(eolvimeo.error_description, 'upload_failed, Lleva mas de 24 hrs procesando o video no tiene formato HD')

    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_vimeo_transcode_preexpiry(self, get_storage, get):
        """
            Test update_video_vimeo when the video takes more than 2 hours but less than 24 hours processing
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_upload',
            error_description = '',
            expiry_at=(datetime.datetime.utcnow() - datetime.timedelta(hours=4))
        )
        get_data = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'complete'}, 'duration':self.video['duration'], 'upload': {'status': 'complete'}, 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'SD 640p', 'size_short': ''}]}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),]
        vimeo_utils.update_video_vimeo()
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        video = get_video_info(self.video["edx_video_id"])
        self.assertEqual(video['status'], 'upload_completed_encoding')
        self.assertEqual(eolvimeo.status, 'upload_completed_encoding')
        self.assertEqual(eolvimeo.error_description, 'upload_completed_encoding, Lleva mas de 2 hrs procesando.')

    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.get_storage")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_vimeo_transcode_no_expiry(self, get_storage, get):
        """
            Test update_video_vimeo when video is still uploading in vimeo
        """
        get_storage.configure_mock(open=Mock(), delete=Mock())
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_upload',
            error_description = '',
            expiry_at=datetime.datetime.utcnow()
        )
        get_data = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'complete'}, 'duration':self.video['duration'], 'upload': {'status': 'complete'}, 'files': [{'quality': 'source', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'SD 640p', 'size_short': ''}]}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),]
        vimeo_utils.update_video_vimeo()
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        video = get_video_info(self.video["edx_video_id"])
        self.assertEqual(video['status'], 'vimeo_encoding')
        self.assertEqual(eolvimeo.status, 'vimeo_encoding')
        self.assertEqual(eolvimeo.error_description, 'Vimeo todavia puede estar procesando el video.')

    @patch('requests.get')
    @patch("eol_vimeo.vimeo_utils.update_video")
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def test_update_video_vimeo_fail_patch(self, mock_update_video, get):
        """
            Test update_video_vimeo when vimeo patch fail
        """
        mock_update_video.side_effect = Exception()
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_upload',
            expiry_at=datetime.datetime.utcnow(),
            error_description = ''
        )
        get_data = {'name':self.video['client_video_id'], 'status':'available', 'transcode': {'status': 'complete'}, 'duration':self.video['duration'], 'upload': {'status': 'complete'}, 'files': [{'quality': 'hd', 'type': 'source', 'width': 0, 'height': 0, 'link': 'https://player.vimeo.com/external/1122233344', 'created_time': '2021-06-08T14:21:04+00:00', 'fps': 30, 'size': 0, 'md5': None, 'public_name': 'Original', 'size_short': ''}]}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),]
        vimeo_utils.update_video_vimeo()
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video["edx_video_id"])
        video = get_video_info(self.video["edx_video_id"])
        self.assertEqual(video['status'], 'vimeo_patch_failed')
        self.assertEqual(eolvimeo.status, 'vimeo_patch_failed')

class TestEolVimeoView(UrlResetMixin, ModuleStoreTestCase):
    def setUp(self):
        super(TestEolVimeoView, self).setUp()
        # create a course
        self.course = CourseFactory.create(
            org='mss', course='999', display_name='eol_test_course')
        aux = CourseOverview.get_from_id(self.course.id)
        self.video = {
            "edx_video_id": "123-456-789",
            "client_video_id": "test.mp4",
            "duration": 10,
            "status": 'vimeo_upload',
            "courses":  [text_type(self.course.id)],
            "created": datetime.datetime.now(pytz.utc),
            "encoded_videos": [],
        }
        self.video2 = {
            "edx_video_id": "789-456-123",
            "client_video_id": "test2.mp4",
            "duration": 10,
            "status": 'vimeo_upload',
            "courses":  [text_type(self.course.id)],
            "created": datetime.datetime.now(pytz.utc),
            "encoded_videos": [],
        }
        self.video3 = {
            "edx_video_id": "345-2323-123",
            "client_video_id": "test3.mp4",
            "duration": 10,
            "status": 'upload_completed',
            "courses":  [text_type(self.course.id)],
            "created": datetime.datetime.now(pytz.utc),
            "encoded_videos": [],
        }
        create_profile("desktop_mp4")
        create_video(self.video)
        create_video(self.video2)
        create_video(self.video3)
        self.client = Client()
        self.client2 = Client()
        self.client3 = Client()
        with patch('common.djangoapps.student.models.cc.User.save'):
            # staff user
            self.user = UserFactory(
                username='testuser2',
                password='12345',
                email='student2@edx.org',
                is_staff=True)
            self.client.login(username='testuser2', password='12345')
            self.instructor = UserFactory(
                username='testinstructor',
                password='12345',
                email='instructor@edx.org')
            self.client2.login(username='testinstructor', password='12345')
            role = CourseInstructorRole(self.course.id)
            role.add_users(self.instructor)
            self.student_user = UserFactory(
                username='student_user',
                password='12345',
                email='student_test@edx.org')
            self.client3.login(username='student_user', password='12345')
        EolVimeoVideo.objects.create(
            edx_video_id = self.video["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_upload',
            error_description = '',
            token='123asd456asd789asd',
            expiry_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=300)
        )
        EolVimeoVideo.objects.create(
            edx_video_id = self.video2["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'vimeo_upload',
            error_description = '',
            token='123asd456asd789asd',
            expiry_at=datetime.datetime.utcnow() - datetime.timedelta(seconds=301)
        )
        EolVimeoVideo.objects.create(
            edx_video_id = self.video3["edx_video_id"],
            user =self.user,
            vimeo_video_id = '1122334455',
            course_key = self.course.id,
            url_vimeo = '',
            status = 'upload_completed',
            error_description = '',
            token='123asd456asd789asd',
            expiry_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=300)
        )

    @patch('eol_vimeo.views.get_url_video')
    def test_vimeo_callback(self, mock_url_video):
        """
            Test vimeo_callback normal process
        """
        mock_url_video.return_value = 'https://s3.test.test.ts/path-video-s3'
        result = self.client.get(
            reverse('vimeo_callback'),
            data={
                'videoid': self.video["edx_video_id"],
                'token': '123asd456asd789asd'})
        self.assertEqual(result.status_code, 302)
        request = urllib.parse.urlparse(result.url)
        self.assertEqual(request.netloc, 's3.test.test.ts')
        self.assertEqual(request.path, '/path-video-s3')
    
    def test_vimeo_callback_wrong_token(self):
        """
            Test vimeo_callback when token is wrong
        """
        result = self.client.get(
            reverse('vimeo_callback'),
            data={
                'videoid': self.video["edx_video_id"],
                'token': 'asdasdadsadad'})
        self.assertEqual(result.status_code, 400)

    def test_vimeo_callback_wrong_id(self):
        """
            Test vimeo_callback when edx_video_id is wrong
        """
        result = self.client.get(
            reverse('vimeo_callback'),
            data={
                'videoid': '456-456789-456',
                'token': '123asd456asd789asd'})
        self.assertEqual(result.status_code, 400)

    def test_vimeo_callback_no_params(self):
        """
            Test vimeo_callback when edx_video_id or token isn ot in url
        """
        result = self.client.get(
            reverse('vimeo_callback'))
        self.assertEqual(result.status_code, 400)

    def test_vimeo_callback_post(self):
        """
            Test vimeo_callback when is POST
        """
        result = self.client.post(
            reverse('vimeo_callback'))
        self.assertEqual(result.status_code, 400)
    
    def test_vimeo_callback_expired(self):
        """
            Test vimeo_callback when token expired
        """
        result = self.client.get(
            reverse('vimeo_callback'),
            data={
                'videoid': self.video2["edx_video_id"],
                'token': '123asd456asd789asd'})
        self.assertEqual(result.status_code, 400)
    
    def test_vimeo_update_picture_wrong_courseid(self):
        """
            Test vimeo_update_picture when course id is wrong
        """
        result = self.client.post(
            reverse('vimeo_update_picture'),
            data={
                'videoid': self.video["edx_video_id"],
                'course_id': 'course-v1:eol+Test101+2021'})
        self.assertEqual(result.status_code, 400)

    def test_vimeo_update_picture_wrong_videoid(self):
        """
            Test vimeo_update_picture when video id is wrong
        """
        result = self.client.post(
            reverse('vimeo_update_picture'),
            data={
                'videoid': '456-456789-456',
                'course_id': str(self.course.id)})
        self.assertEqual(result.status_code, 400)

    def test_vimeo_update_picture_no_params(self):
        """
            Test vimeo_update_picture when edx_video_id or token isn ot in url
        """
        result = self.client.post(
            reverse('vimeo_update_picture'))
        self.assertEqual(result.status_code, 400)

    def testvimeo_update_picture_get(self):
        """
            Test vimeo_update_picture when is GET
        """
        result = self.client.get(
            reverse('vimeo_update_picture'))
        self.assertEqual(result.status_code, 400)
    
    def testvimeo_update_picture_annonimous_user(self):
        """
            Test vimeo_update_picture when user is annonimous
        """
        client = Client()
        result = client.post(
            reverse('vimeo_update_picture'),
            data={
                'videoid': self.video["edx_video_id"],
                'course_id': str(self.course.id)})
        self.assertEqual(result.status_code, 400)
    
    def testvimeo_update_picture_student_user(self):
        """
            Test vimeo_update_picture when user is student
        """
        result = self.client3.post(
            reverse('vimeo_update_picture'),
            data={
                'videoid': self.video["edx_video_id"],
                'course_id': str(self.course.id)})
        self.assertEqual(result.status_code, 400)
    
    @patch('requests.get')
    @override_settings(EOL_VIMEO_CLIENT_ID='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_SECRET='1234567890asdfgh')
    @override_settings(EOL_VIMEO_CLIENT_TOKEN='1234567890asdfgh')
    def testvimeo_update_picture_instructor_user(self, get):
        """
            Test vimeo_update_picture when user is instructor
        """
        get_data = {'pictures': {'base_link': 'this is a picture url'}}
        get.side_effect = [namedtuple("Request", ["status_code", "json"])(200, lambda:get_data),]
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video3["edx_video_id"], course_key=self.course.id)
        self.assertEqual(eolvimeo.url_picture, '')
        result = self.client2.post(
            reverse('vimeo_update_picture'),
            data={
                'videoid': self.video3["edx_video_id"],
                'course_id': str(self.course.id)})
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json(), {'result':'success'})
        eolvimeo = EolVimeoVideo.objects.get(edx_video_id=self.video3["edx_video_id"], course_key=self.course.id)
        self.assertEqual(eolvimeo.url_picture, 'this is a picture url')