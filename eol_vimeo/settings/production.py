def plugin_settings(settings):
    settings.EOL_VIMEO_CLIENT_ID = settings.ENV_TOKENS.get('EOL_VIMEO_CLIENT_ID', '')
    settings.EOL_VIMEO_CLIENT_SECRET = settings.ENV_TOKENS.get('EOL_VIMEO_CLIENT_ID', '')
    settings.EOL_VIMEO_CLIENT_TOKEN = settings.ENV_TOKENS.get('EOL_VIMEO_CLIENT_ID', '')
    settings.EOL_VIMEO_MAIN_FOLDER = settings.ENV_TOKENS.get('EOL_VIMEO_CLIENT_ID', 'Studio Eol')
    settings.EOL_VIMEO_DOMAINS = settings.ENV_TOKENS.get('EOL_VIMEO_CLIENT_ID', [])