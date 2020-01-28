from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from .models import Users, PlaylistDetails, SpotifyToken, ArtistsInPlaylist
from . import db
import sys
import spotipy
import spotipy.util as util
from spotipy import oauth2
import os
from .helpers import refresh_access_token, get_access_and_refresh

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/profile')
@login_required
def profile():
	global sp
	user = Users.query.filter_by(email=current_user.email).first()
	code = request.args.get('code')

	if code:
		user.spot_auth = True
		token_info = get_access_and_refresh(code)
		spotify_token = SpotifyToken(user.id, token_info['access_token'], token_info['refresh_token'])
		db.session.add(spotify_token)
		db.session.commit()

	access_token = SpotifyToken.query.filter_by(user_id=user.id).first().access_token

	if not code:
		access_token = refresh_access_token(SpotifyToken.query.filter_by(user_id=user.id).first().refresh_token)
		user_spot_info = SpotifyToken.query.filter_by(user_id=user.id).first()
		user_spot_info.access_token = access_token
		db.session.commit()

	sp = spotipy.Spotify(auth=access_token)
	playlist_links = PlaylistDetails.query.filter_by(user_id=user.id).all()
	return render_template('default_profile.html', name=current_user.first_name, user_type=user.user_type,
							playlist_links=playlist_links)


@main.route('/check_playlist', methods=['POST'])
@login_required
def check_playlist():
	user = Users.query.filter_by(email=current_user.email).first()
	uri = request.form.get('playlist_uri')
	playlist = sp.playlist(playlist_id=uri, fields='name,followers,tracks')
	playlist_links = [playlist['uri'] for playlist in PlaylistDetails.query.filter_by(user_id=user.id).all()]
	if (playlist['followers']['total']) < 750:
		return render_template('default_profile.html', name=current_user.first_name, user_type=user.user_type,
							playlist_links=playlist_links, too_short=True)

	if PlaylistDetails.query.filter_by(playlist_uri=uri).first() is None:
		playlist_details = PlaylistDetails(user.id, playlist['name'], uri, playlist['followers']['total'], 
											len(playlist['tracks']['items']), 0)
		db.session.add(playlist_details)
		db.session.commit()

	for track in playlist['tracks']['items']:
		artist_name = track['track']['artists'][0]['name']
		artist_in_paylist = ArtistsInPlaylist(PlaylistDetails.query.filter_by(playlist_uri=uri).first().id, 
												artist_name=artist_name)
		db.session.add(artist_in_paylist)
		db.session.commit()
	playlist_links = PlaylistDetails.query.filter_by(user_id=user.id).all()

	return render_template('default_profile.html', name=current_user.first_name, user_type=user.user_type,
							playlist_links=playlist_links, too_short=False)

    