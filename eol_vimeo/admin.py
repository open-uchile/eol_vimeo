from django.contrib import admin
from .models import EolVimeoVideo

class EolVimeoVideoAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('user', 'edx_video_id', 'status')
    search_fields = ['user__username', 'edx_video_id', 'status']
    ordering = ['-user__username']

admin.site.register(EolVimeoVideo, EolVimeoVideoAdmin)