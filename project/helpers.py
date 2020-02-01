import spotipy
import spotipy.util as util
import os
import numpy as np
from spotipy import oauth2

from .models import Users, SpotifyToken

scopes = 'playlist-modify-public'
sp_oauth = oauth2.SpotifyOAuth(client_id=os.environ['CLIENT_ID'], 
                                    client_secret=os.environ['CLIENT_SECRET'],
                                    redirect_uri=os.environ['REDIRECT_URI'],
                                    scope=scopes)


def get_auth_url():
    auth_url = sp_oauth.get_authorize_url(show_dialog=False)
    return auth_url

def get_access_and_refresh(code):
    return sp_oauth.get_access_token(code)


def refresh_access_token(refresh_token):
    token_info = sp_oauth.refresh_access_token(refresh_token)
    token = token_info['access_token']
    return token

def get_playlist_genre(artist_list, sp):
    artist_list = np.array_split(artist_list, 5)
    artists = []
    for artist in artist_list:
        artists += sp.artists(artist)['artists']
    artist_genres = [artist['genres'] for artist in artists if artist is not None]
    artist_genres = [genre for sublist in artist_genres for genre in sublist]
    genre_dict = {}
    for genre in artist_genres:
        if genre in genre_dict:
            genre_dict[genre] += 1
        else:
            genre_dict[genre] = 1
    return max(genre_dict, key=genre_dict.get)


        