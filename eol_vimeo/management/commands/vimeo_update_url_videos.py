from django.core.management.base import BaseCommand, CommandError

from opaque_keys.edx.keys import CourseKey
from django.contrib.auth.models import User
from django.conf import settings
from eol_vimeo.vimeo_utils import update_edxval_url, check_credentials, get_video_vimeo, get_link_video, get_storage
from eol_vimeo.models import EolVimeoVideo
import datetime
from django.utils import timezone

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'This command will Update path video from video with status "vimeo_encoding".'

    def handle(self, *args, **options):
        """
            Update path video from video with status 'vimeo_encoding'
        """
        if check_credentials():
            videos_to_patch = EolVimeoVideo.objects.filter(status='vimeo_encoding')
            for video in videos_to_patch:
                video_data = get_video_vimeo(video.vimeo_video_id)
                if len(video_data) == 0:
                    logger.info('EolVimeoCommand - Video not found in vimeo, edx_video_id: {}'.format(video.edx_video_id))
                    video.error_description = 'No se pudo obtener el video en Vimeo.'
                    video.status = 'vimeo_not_found'
                    video.save()
                elif 'upload' not in video_data or video_data['upload']['status'] == 'error':
                    logger.info('EolVimeoCommand - video was not uploaded correctly, edx_video_id: {}, id_vimeo: {}'.format(video.edx_video_id, video.vimeo_video_id))
                    video.error_description = 'Error en subir video a Vimeo'
                    video.status = 'vimeo_not_found'
                    video.save()
                elif 'files' not in video_data or len(video_data['files']) == 0:
                    logger.info('EolVimeoCommand - Token User Vimeo have Basic plan, edx_video_id: {}'.format(video.edx_video_id))
                    video.error_description = 'Token Usuario Vimeo tiene plan Basic.'
                    video.save()
                elif len(video_data['files']) == 1 and video_data['files'][0]['public_name'] == 'Original':
                    logger.info('EolVimeoCommand - Video is still processing, edx_video_id: {}'.format(video.edx_video_id))
                    video.error_description = 'Vimeo todavia esta procesando el video.'
                    video.save()
                else:
                    quality_video = get_link_video(video_data)
                    video_name = '{} {}'.format(video_data['name'], quality_video['public_name'])
                    is_updated = update_edxval_url(video.edx_video_id, quality_video['link'], quality_video['size'], video_name, video_data['duration'], 'upload_completed')
                    if is_updated:
                        logger.info('EolVimeoCommand - Video upload completed, edx_video_id: {}'.format(video.edx_video_id))
                        video.url_vimeo = quality_video['link']
                        video.error_description = ''
                        video.status = 'upload_completed'
                        get_storage().delete(video.edx_video_id)
                    else:
                        logger.info('EolVimeoCommand - Error to update video in edxval.api, edx_video_id: {}'.format(video.edx_video_id))
                        video.error_description = 'No se pudo agregar el path vimeo del video al video en plataforma(error update_video in edxval.api).'
                        video.status = 'vimeo_patch_failed'
                    video.save()
        else:
            logger.info('EolVimeo - Credentials are not defined')
        