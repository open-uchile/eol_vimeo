# EOL Vimeo

![https://github.com/open-uchile/eol_vimeo/actions](https://github.com/open-uchile/eol_vimeo/workflows/Python%20application/badge.svg) ![Coverage Status](https://github.com/eol-uchile/eol_vimeo/blob/master/coverage-badge.svg)

Upload videos to Vimeo.

# Install App

    docker-compose exec cms pip install -e /openedx/requirements/eol_vimeo
    docker-compose exec lms pip install -e /openedx/requirements/eol_vimeo
    docker-compose exec cms_worker pip install -e /openedx/requirements/eol_vimeo
    docker-compose exec cms python manage.py cms --settings=prod.production makemigrations eol_vimeo
    docker-compose exec cms python manage.py cms --settings=prod.production migrate eol_vimeo

# Configuration Vimeo

To enable [Vimeo API](https://developer.vimeo.com/api/guides/start) Add this configuration in `CMS.yml` and add your own keys and domains url.

    EOL_VIMEO_CLIENT_ID: ''
    EOL_VIMEO_CLIENT_SECRET: ''
    EOL_VIMEO_CLIENT_TOKEN: ''
    EOL_VIMEO_MAIN_FOLDER: 'Studio Eol'
    EOL_VIMEO_DOMAINS: ['your-domain.com', 'studio.your-domain.com']

# Setup Vimeo for S3

Add this configuration in `production.py`

    VIMEO_STORAGE_CLASS = {
        'class': 'storages.backends.s3boto3.S3Boto3Storage',
        'options': {
            'location': '',
            'bucket_name': 'bucketname'
        }
    }
    VIMEO_STORAGE_CLASS = ENV_TOKENS.get('VIMEO_STORAGE_CLASS', VIMEO_STORAGE_CLASS)

# Setup VIDEO PIPELINE

Add this configuration in `LMS` & `CMS` .yml:

    FEATURES:
        ENABLE_VIDEO_UPLOAD_PIPELINE: true
    VIDEO_UPLOAD_PIPELINE:
        BUCKET: 'bucketname'
        ROOT_PATH: ''
        VEM_S3_BUCKET: 'bucketname'

# Configuration Video PIPELINE

- To enable video pipeline add `your-domain.com/admin/video_pipeline/videouploadsenabledbydefault/`, you can enable for all course too.
- To enable video pipeline by course, add course_id here `your-domain.com/admin/video_pipeline/coursevideouploadsenabledbydefault/`.

# Install

- Edit the following file to add the upload_vimeo function _/openedx/edx-platform/cms/djangoapps/contentstore/views/videos.py_

        from django.db import transaction
        from lms.djangoapps.instructor_task.api_helper import AlreadyRunningError
        try:
            from eol_vimeo.vimeo_task import task_process_data
            from eol_vimeo.vimeo_utils import update_create_vimeo_model
            ENABLE_EOL_VIMEO = True
        except ImportError:
            ENABLE_EOL_VIMEO = False
        ...
        class StatusDisplayStrings:
            ...
            _STATUS_MAP["vimeo_encoding"] = _IN_PROGRESS
        ...
        def vimeo_task(request, course_id, data):
            try:
                task = task_process_data(request, course_id, data)
                return True
            except AlreadyRunningError:
                LOGGER.error("EolVimeo - Task Already Running Error, user: {}, course_id: {}".format(request.user, course_id))
                return False
        ...
        @transaction.non_atomic_requests
        def videos_handler(request, course_key_string, edx_video_id=None):
            ...
            else:
                if is_status_update_request(request.json):
                    if ENABLE_EOL_VIMEO:
                        upload_completed_videos = []
                        for video in request.json:
                            status = video.get('status')
                            if status == 'upload_completed':
                                upload_completed_videos.append(video)
                                status = 'upload'
                            update_video_status(video.get('edxVideoId'), status)
                            update_create_vimeo_model(video.get('edxVideoId'), request.user.id, status, video.get('message'), course_key_string)
                            LOGGER.info(
                                u'VIDEOS: Video status update with id [%s], status [%s] and message [%s]',
                                video.get('edxVideoId'),
                                status,
                                video.get('message')
                            )
                        if len(upload_completed_videos) > 0:
                            status_vimeo_task = vimeo_task(request, course_key_string, upload_completed_videos)
                        return JsonResponse()
                    else:
                        LOGGER.info('EolVimeo is not installed')
                        return send_video_status_update(request.json)
                elif _is_pagination_context_update_request(request):
                    return _update_pagination_context(request)

                data, status = videos_post(course, request)
                return JsonResponse(data, status=status)
        ...
        def videos_post(course, request):
            ...
            key = storage_service_key(bucket, file_name=edx_video_id)
            if ENABLE_EOL_VIMEO:
                upload_url = key.generate_url(
                    KEY_EXPIRATION_IN_SECONDS,
                    'PUT'
                )
            else:
                metadata_list = [
                    ('client_video_id', file_name),
                    ('course_key', str(course.id)),
                ]
                deprecate_youtube = waffle_flags()[DEPRECATE_YOUTUBE]
                course_video_upload_token = course.video_upload_pipeline.get('course_video_upload_token')

                # Only include `course_video_upload_token` if youtube has not been deprecated
                # for this course.
                if not deprecate_youtube.is_enabled(course.id) and course_video_upload_token:
                    metadata_list.append(('course_video_upload_token', course_video_upload_token))

                is_video_transcript_enabled = VideoTranscriptEnabledFlag.feature_enabled(course.id)
                if is_video_transcript_enabled:
                    transcript_preferences = get_transcript_preferences(str(course.id))
                    if transcript_preferences is not None:
                        metadata_list.append(('transcript_preferences', json.dumps(transcript_preferences)))

                for metadata_name, value in metadata_list:
                    key.set_metadata(metadata_name, value)
                upload_url = key.generate_url(
                    KEY_EXPIRATION_IN_SECONDS,
                    'PUT',
                    headers={'Content-Type': req_file['content_type']})
        ...
        def storage_service_bucket():
            if waffle_flags()[ENABLE_DEVSTACK_VIDEO_UPLOADS].is_enabled():
                params = {
                    'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
                    'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
                    'security_token': settings.AWS_SECURITY_TOKEN,
                    'host': settings.AWS_S3_ENDPOINT_DOMAIN
                }
            else:
                params = {
                    'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
                    'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
                    'host': settings.AWS_S3_ENDPOINT_DOMAIN
                }
            conn = s3.connection.S3Connection(**params)
            return conn.get_bucket(settings.VIDEO_UPLOAD_PIPELINE['VEM_S3_BUCKET'], validate=False)

## Update Video link

    > docker-compose exec cms python manage.py cms --settings=prod.production vimeo_update_url_videos

## TESTS
**Prepare tests:**

    > cd .github/
    > docker-compose run cms /openedx/requirements/eol_vimeo/.github/test.sh

## Notes
- The video is deleted from the storage once uploaded to vimeo, if the video has a status other than 'upload_completed' at the beginning of the task, it will not be deleted.
- If you delete a video from the video table, it will not be deleted, it will only change the 'status' of the video.
- The link of the video obtained from vimeo to view, is an initial link because the video is still being processed when the link is obtained.
- If status video is 'upload' for 24 hours it change to 'upload_failed'.
