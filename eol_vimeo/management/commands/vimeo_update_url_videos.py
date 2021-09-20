from django.core.management.base import BaseCommand, CommandError

from opaque_keys.edx.keys import CourseKey
from django.contrib.auth.models import User
from django.conf import settings
from eol_vimeo.vimeo_utils import update_video_vimeo

import datetime
from django.utils import timezone

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'This command will Update path video from video with status "vimeo_encoding, vimeo_upload".'

    def handle(self, *args, **options):
        """
            Update path video from video with status 'vimeo_encoding'
        """
        logger.info('EolVimeoCommand - Running vimeo_utils.update_video_vimeo()')
        update_video_vimeo()
