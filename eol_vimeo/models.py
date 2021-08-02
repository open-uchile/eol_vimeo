from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from opaque_keys.edx.django.models import CourseKeyField

# Create your models here.
URL_REGEX = '^[a-zA-Z0-9\\-_]*$'

class EolVimeoVideo(models.Model):
    class Meta:
        index_together = [
            ["edx_video_id", "course_key"],
        ]
        unique_together = [
            ["edx_video_id", "course_key"],
        ]
    edx_video_id = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=URL_REGEX,
                message='edx_video_id has invalid characters',
                code='invalid edx_video_id'
            ),
        ]
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vimeo_video_id = models.CharField(max_length=50, blank=True)
    course_key = CourseKeyField(max_length=255, default=None, blank=True)
    url_vimeo = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=50, blank=True)
    error_description = models.TextField('Error Description', blank=True, null=True)