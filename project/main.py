from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from .models import Users, PlaylistDetails, SpotifyToken, ArtistsInPlaylist, ArtistTracks, SimilarArtists
from . import db
import sys
import re
import spotipy
import spotipy.util as util
from spotipy import oauth2
import os
from .helpers import refresh_access_token, get_access_and_refresh, get_playlist_genre, \
						get_curr_artist_tracks, get_curr_similar_artists

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')


@main.route('/profile')
@login_required
def profile():
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

	if user.user_type == 1:
		return redirect(url_for('main.playlister_profile'))
	elif user.user_type == 2:
		return redirect(url_for('main.artist_profile'))


@main.route('/playlister_profile')
@login_required
def playlister_profile():
	user = Users.query.filter_by(email=current_user.email).first()
	playlist_dict = PlaylistDetails.query.filter_by(user_id=user.id).all()
	return render_template('playlister_profile.html', name=current_user.first_name,
							playlist_dict=playlist_dict)

@main.route('/playlister_profile', methods=['POST'])
@login_required
def check_playlist():
	user = Users.query.filter_by(email=current_user.email).first()
	uri = request.form.get('playlist_uri')
	if uri is "": return render_template('playlister_profile.html', name=current_user.first_name,
							playlist_dict=PlaylistDetails.query.filter_by(user_id=user.id).all())

	access_token = refresh_access_token(SpotifyToken.query.filter_by(user_id=user.id).first().refresh_token)
	user_spot_info = SpotifyToken.query.filter_by(user_id=user.id).first()
	user_spot_info.access_token = access_token
	db.session.commit()

	sp = spotipy.Spotify(auth=access_token)

	playlist = sp.playlist(playlist_id=uri, fields='name,followers,tracks')
	
	playlist_links = [playlist.playlist_uri for playlist in PlaylistDetails.query.filter_by(user_id=user.id).all()]
	if (playlist['followers']['total']) < 750:
		return render_template('playlister_profile.html', name=current_user.first_name, too_short=True,
							playlist_dict=PlaylistDetails.query.filter_by(user_id=user.id).all())

	if PlaylistDetails.query.filter_by(playlist_uri=uri).first() is None:
		overall_genre = get_playlist_genre([track['track']['artists'][0]['uri'] for 
											track in playlist['tracks']['items']], sp)
		playlist_details = PlaylistDetails(user.id, playlist['name'], uri, playlist['followers']['total'], 
											len(playlist['tracks']['items']), 0, overall_genre)
		db.session.add(playlist_details)
		db.session.commit()

		for track in playlist['tracks']['items']:
			artist_name = track['track']['artists'][0]['name']
			artist_in_paylist = ArtistsInPlaylist(PlaylistDetails.query.filter_by(playlist_uri=uri).first().id, 
													artist_name=re.sub('[^A-Za-z0-9]+', ' ', artist_name))
			db.session.add(artist_in_paylist)
			db.session.commit()
	return render_template('playlister_profile.html', name=current_user.first_name, too_short=False,
							playlist_dict=PlaylistDetails.query.filter_by(user_id=user.id).all())


@main.route('/artist_profile')
@login_required
def artist_profile():
	user = Users.query.filter_by(email=current_user.email).first()
	access_token = refresh_access_token(SpotifyToken.query.filter_by(user_id=user.id).first().refresh_token)
	user_spot_info = SpotifyToken.query.filter_by(user_id=user.id).first()
	user_spot_info.access_token = access_token
	db.session.commit()

	sp = spotipy.Spotify(auth=access_token)
	return render_template('artist_profile.html', user_name=user.first_name, tracks=get_curr_artist_tracks(user.id),
														related_artists=get_curr_similar_artists(user.id, sp)) 

@main.route('/artist_profile', methods=['POST'])
@login_required
def artist_song():
	user = Users.query.filter_by(email=current_user.email).first()
	access_token = refresh_access_token(SpotifyToken.query.filter_by(user_id=user.id).first().refresh_token)
	user_spot_info = SpotifyToken.query.filter_by(user_id=user.id).first()
	user_spot_info.access_token = access_token
	db.session.commit()

	sp = spotipy.Spotify(auth=access_token)

	song_uri = request.form.get('song_uri')
	artist_uris = [request.form.get('similar_artist1_uri'), 
					request.form.get('similar_artist2_uri'), 
					request.form.get('similar_artist3_uri'),
					request.form.get('similar_artist4_uri'), 
					request.form.get('similar_artist5_uri')]
	song_description = request.form.get('song_description') if request.form.get('song_description') is not None else ""

	try:
		song_details = sp.track(song_uri)
	except spotipy.client.SpotifyException as e:
		return render_template('artist_profile.html', user_name=user.first_name,
														tracks=get_curr_artist_tracks(user.id),
														related_artists=get_curr_similar_artists(user.id, sp),
														exception="There was an issue retrieving your \
																requested track from Spotify, please \
																check your URI, make sure it is a track \
																link not an album one and try again")
	song_artist_name = song_details['artists'][0]['name']
	song_artist_uri = song_details['artists'][0]['uri']
	song_img = song_details['album']['images'][2]['url']

	try:
		all_artists = sp.artists(artist_uris)['artists']
	except spotipy.client.SpotifyException as e:
		return render_template('artist_profile.html', user_name=user.first_name, 
														tracks=get_curr_artist_tracks(user.id),
														related_artists=get_curr_similar_artists(user.id, sp),
														exception="There was an issue retrieving your similar \
																	artrists from Spotify, please make sure \
																		your URIs are correct and try again.")
	
	genres = [artist['genres'] for artist in all_artists]
	genres = [genre for sublist in genres for genre in sublist]

	similar_playlists = PlaylistDetails.query.filter(PlaylistDetails.genre.in_(genres)).all()
	similar_playlist_ids = [playlist.playlist_uri.split(':')[2] for playlist in similar_playlists]
	playlist_embed_urls = ["https://open.spotify.com/embed/playlist/%s" % p_id for p_id in similar_playlist_ids]

	new_track = ArtistTracks(user.id, song_details['name'], song_description, 
								song_details['external_urls']['spotify'], song_uri, None)
	db.session.add(new_track)
	db.session.commit()

	if SimilarArtists.query.filter_by(artist_id=user.id).first() is None:
		similar_artists = SimilarArtists(user.id, request.form.get('similar_artist1_uri'), 
										request.form.get('similar_artist2_uri'),
										request.form.get('similar_artist3_uri'), 
										request.form.get('similar_artist4_uri'),
										request.form.get('similar_artist5_uri'))
		db.session.add(similar_artists)
	else:
		curr_sim_artists = SimilarArtists.query.filter_by(artist_id=user.id).first()
		curr_sim_artists.similar_artist_1 = request.form.get('similar_artist1_uri')
		curr_sim_artists.similar_artist_2 = request.form.get('similar_artist2_uri')
		curr_sim_artists.similar_artist_3 = request.form.get('similar_artist3_uri')
		curr_sim_artists.similar_artist_4 = request.form.get('similar_artist4_uri')
		curr_sim_artists.similar_artist_5 = request.form.get('similar_artist5_uri')
	db.session.commit()

	return render_template('artist_profile.html', song_img=song_img, song_description=song_description,
							playlist_embed_urls=playlist_embed_urls, tracks=get_curr_artist_tracks(user.id),
							related_artists=get_curr_similar_artists(user.id, sp), user_name=user.first_name)
	
