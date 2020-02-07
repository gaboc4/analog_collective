import spotipy
import spotipy.util as util
import os
import numpy as np
from spotipy import oauth2
from collections import OrderedDict

from .models import Users, SpotifyToken, SimilarArtists, ArtistTracks, PlaylistDetails

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


def get_curr_sim_artists(user_id, sp):
    sa = SimilarArtists.query.filter_by(artist_id=user_id).first()
    if sa is not None:
        return {'similar_artist_1': sp.artist(sa.similar_artist_1)['name'],
                'similar_artist_2': sp.artist(sa.similar_artist_2)['name'],
                'similar_artist_3': sp.artist(sa.similar_artist_3)['name'],
                'similar_artist_4': sp.artist(sa.similar_artist_4)['name'],
                'similar_artist_5': sp.artist(sa.similar_artist_5)['name']}
    else:
        return None

def get_curr_artist_tracks(user_id):
    tracks = ArtistTracks.query.filter_by(artist_id=user_id).all()
    final_list_of_tracks = []
    for track in tracks:
        track_dict = OrderedDict()
        track_dict['track_name'] = track.track_name
        track_dict['track_link'] = track.track_link
        track_dict['track_summary'] = track.track_summary
        if track.placed_playlist_id is None:
            track_dict['playlist'] = ""
        else:
            track_dict['playlist'] = PlaylistDetails.query.filter_by(id=track.placed_playlist_id).first().name
        final_list_of_tracks.append(track_dict)
    return final_list_of_tracks
