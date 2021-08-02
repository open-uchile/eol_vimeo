from django.contrib import admin
from .models import EolVimeoVideo

class EolVimeoVideoAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('course_key', 'user', 'edx_video_id', 'status')
    search_fields = ['course_key', 'user__username', 'edx_video_id', 'status']
    ordering = ['-course_key']

admin.site.register(EolVimeoVideo, EolVimeoVideoAdmin)