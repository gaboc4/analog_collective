def refresh_token(token_info):
    token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    token = token_info['access_token']
    sp = spotipy.Spotify(auth=token)
    return