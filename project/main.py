# main.py

from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from .models import Users, PlaylistUri, SpotifyToken
from . import db
import sys
import spotipy
import spotipy.util as util
from spotipy import oauth2

main = Blueprint('main', __name__)

scopes = 'playlist-modify-public'

sp_oauth = oauth2.SpotifyOAuth(client_id='e2141c4d6523483082e21d27558b1217',
									client_secret='198d638c1f2f4cad821c21f9b25cc60e',
									redirect_uri='http://127.0.0.1:5000/profile',
									scope=scopes)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/profile')
@login_required
def profile():
	global sp
	user = Users.query.filter_by(email=current_user.email).first()
	code = request.args.get('code')
	if not code:
		token_info = SpotifyToken.query.filter_by(user_id=user.id).first()
		if not token_info:
			auth_url = sp_oauth.get_authorize_url(show_dialog=False)
			return render_template('default_profile.html', auth_url=auth_url)

	access_token = SpotifyToken.query.filter_by(user_id=user.id).first().access_token
	if not access_token:
		token_info = sp_oauth.get_access_token(code)
		spotify_token = SpotifyToken(user.id, token_info['access_token'], token_info['refresh_token'])
		db.session.add(spotify_token)
		db.session.commit()
		sp = spotipy.Spotify(auth=token_info['access_token'])

	sp = spotipy.Spotify(auth=access_token)
	playlist_links = PlaylistUri.query.filter_by(user_id=user.id).all()
	return render_template('default_profile.html', name=current_user.first_name, user_type=user.user_type,
							playlist_links=playlist_links)


@main.route('/check_playlist', methods=['POST'])
@login_required
def check_playlist():

	uri = request.form.get('playlist_uri')
	playlist = sp.playlist_tracks(playlist_id=uri)
	print(playlist)
	# spotify:playlist:7rQpgybgIaYGZtDGHLj5T7
	# token = util.prompt_for_user_token(current_user.email, scope, client_id='e2141c4d6523483082e21d27558b1217',
	# 									client_secret='198d638c1f2f4cad821c21f9b25cc60e')

	# token_info = sp_oauth.get_cached_token() 
	# user = Users.query.filter_by(email=current_user.email).first()
	# token_info = SpotifyToken.query.filter_by(user_id=user.id).first()

	# if not token_info:
	# 	auth_url = sp_oauth.get_authorize_url(show_dialog=True)  

	# 	code = sp_oauth.parse_response_code(response)
	# 	token_info = sp_oauth.get_access_token(code)

		# user = Users.query.filter_by(email=current_user.email).first()
		# spotify_token = SpotifyToken(user.id, token_info['access_token'], token_info['refresh_token'])
		# db.session.add(spotify_token)
		# db.session.commit()

	# sp = spotipy.Spotify(auth=token_info['access_token'])

	# if sp_oauth.is_token_expired(token_info):
	#     token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
	#     token = token_info['access_token']
	#     sp = spotipy.Spotify(auth=token)


	return redirect(url_for('main.profile'))

    