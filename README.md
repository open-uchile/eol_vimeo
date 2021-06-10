# EOL Vimeo

![https://github.com/eol-uchile/eol_vimeo/actions](https://github.com/eol-uchile/eol_vimeo/workflows/Python%20application/badge.svg)

Upload videos to vimeo

# Install App

    docker-compose exec cms pip install -e /openedx/requirements/eol_vimeo
    docker-compose exec cms_worker pip install -e /openedx/requirements/eol_vimeo

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
        ...
        def vimeo_task(request, course_id, data):
            try:
                from eol_vimeo.vimeo_task import task_process_data
                task = task_process_data(request, course_id, data)
                return True
            except ImportError:
                LOGGER.info('EolVimeo is not installed')
                return False
            except AlreadyRunningError:
                LOGGER.error("EolVimeo - Task Already Running Error, user: {}, course_id: {}".format(request.user, course_id))
                return False
        ...
        @transaction.non_atomic_requests
        def videos_handler(request, course_key_string, edx_video_id=None):
            ...
            else:
                if is_status_update_request(request.json):
                    try:
                        from eol_vimeo import vimeo_utils
                        for video in request.json:
                            status = video.get('status')
                            if status == 'upload_completed':
                                status = 'upload'
                            update_video_status(video.get('edxVideoId'), status)
                            LOGGER.info(
                                u'VIDEOS: Video status update with id [%s], status [%s] and message [%s]',
                                video.get('edxVideoId'),
                                status,
                                video.get('message')
                            )
                        status_vimeo_task = vimeo_task(request, course_key_string, request.json)
                        return JsonResponse()
                    except ImportError:
                        LOGGER.info('EolVimeo is not installed')
                        return send_video_status_update(request.json)
                elif _is_pagination_context_update_request(request):
                    return _update_pagination_context(request)

                data, status = videos_post(course, request)
                return JsonResponse(data, status=status)

## TESTS
**Prepare tests:**

    > cd .github/
    > docker-compose run cms /openedx/requirements/eol_vimeo/.github/test.sh

## Notes
- The video is deleted from the storage once uploaded to vimeo, if the video has a status other than 'upload_completed' at the beginning of the task, it will not be deleted.
- If you delete a video from the video table, it will not be deleted, it will only change the 'status' of the video.
- The link of the video obtained from vimeo to view, is an initial link because the video is still being processed when the link is obtained.
