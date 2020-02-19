import json
import re
import spotipy
import os
import stripe
import time
from flask import Blueprint, render_template, redirect, url_for, request, flash, get_flashed_messages
from flask_login import login_required, current_user

from .models import Users, PlaylistDetails, SpotifyToken, ArtistsInPlaylist, \
	ArtistTracks, SimilarArtists
from . import db
from .helpers import refresh_access_token, get_access_and_refresh, \
	get_playlist_genre, get_curr_artist_tracks, get_curr_sim_artists, refresh_playlist_deets

main = Blueprint('main', __name__)

stripe.api_key = os.environ['STRIPE_KEY']

credits_info = "These tokens represent how much money you have put " \
               "into the platform in order to add your songs to a playlist. " \
               "You can add more to your account from the Store page!"


@main.route('/')
def index():
	return render_template('index.html')


@main.route('/stripe_approval', methods=['POST'])
@login_required
def authorize_stripe():
	user = Users.query.filter_by(email=current_user.email).first()
	if request.form['tos_accept']:
		try:
			# stripe.Account.create_person(
			# 	user.payment_info,
			# 	first_name=user.first_name,
			# 	last_name=user.last_name,
			# 	ssn_last_4=request.form.get('ssn_last_4')
			# )
			mod_account = stripe.Account.modify(
				user.payment_info,
				tos_acceptance={
					'date': int(time.time()),
					'ip': '127.0.0.1',
				},
				business_type="individual",
				individual={
					"email": user.email,
					"first_name": user.first_name,
					"last_name": user.last_name,
					"phone": request.form.get('phone'),
					"address": {
						"city": request.form.get('city'),
						"state": request.form.get('state'),
						"line1": request.form.get('line1'),
						"line2": request.form.get('line2'),
						"postal_code": request.form.get('postal_code')
					},
					"dob": {
						"day": request.form.get('dob_day'),
						"month": request.form.get('dob_month'),
						"year": request.form.get('dob_year')
					},
					"ssn_last_4": int(request.form.get('ssn_last_4'))
				}
			)
			stripe.Account.create_external_account(
				user.payment_info,
				external_account={
					"object": "bank_account",
					"account_holder_name": user.first_name + " " + user.last_name,
					"account_holder_type": "individual",
					"country": "US",
					"currency": "usd",
					"account_number": request.form.get('account_number'),
					"routing_number": request.form.get('routing_number')
				}
			)
			print(mod_account)
			user.stripe_approval_needed = False
			db.session.commit()
		except stripe.error.InvalidRequestError as e:
			print(e.error.message)
			flash(e.error.message)
			redirect(url_for('main.playlister_profile'))
		return redirect(url_for('main.playlister_profile'))
	return redirect(url_for('main.index'))


@main.route('/profile')
@login_required
def profile():
	user = Users.query.filter_by(email=current_user.email).first()
	code = request.args.get('code')

	if code:
		user.spot_auth = True
		token_info = get_access_and_refresh(code)
		sp = spotipy.Spotify(auth=token_info['access_token'])
		spotify_token = SpotifyToken(user.id, token_info['access_token'], token_info['refresh_token'], sp.me()['id'])
		db.session.add(spotify_token)
		db.session.commit()

	if user.user_type == 1:
		if user.payment_info is None:
			new_account = stripe.Account.create(
				type="custom",
				country="US",
				email=current_user.email,
				business_profile={"product_description": "Analog Collective playlister account for payouts"},
				requested_capabilities=["card_payments", "transfers"])
			user.payment_info = new_account['id']
			user.stripe_approval_needed = True
			db.session.commit()
		return redirect(url_for('main.playlister_profile'))
	elif user.user_type == 2:
		return redirect(url_for('main.artist_profile'))


@main.route('/playlister_profile')
@login_required
def playlister_profile():
	user = Users.query.filter_by(email=current_user.email).first()
	sp = refresh_access_token(SpotifyToken.query.filter_by(user_id=user.id).first().refresh_token, user.id)

	playlist_dict = PlaylistDetails.query.filter_by(user_id=user.id).all()

	if len(playlist_dict) != 0:
		for p in playlist_dict:
			refresh_playlist_deets(p.playlist_uri, sp)

	if user.stripe_approval_needed:
		years = [x for x in range(1950, 2020)]
		days = [x for x in range(1, 32)]
		return render_template('playlister_profile.html', name=current_user.first_name, playlist_dict=playlist_dict,
		                       approval_needed=True, years=years, days=days)

	return render_template('playlister_profile.html', name=current_user.first_name, playlist_dict=playlist_dict)


@main.route('/playlister_profile', methods=['POST'])
@login_required
def check_playlist():
	user = Users.query.filter_by(email=current_user.email).first()
	uri = request.form.get('playlist_uri')
	if uri is "":
		return render_template('playlister_profile.html', name=current_user.first_name,
		                       playlist_dict=PlaylistDetails.query.filter_by(user_id=user.id).all())

	sp = refresh_access_token(SpotifyToken.query.filter_by(user_id=user.id).first().refresh_token, user.id)

	playlist = sp.playlist(playlist_id=uri, fields='name,followers,tracks')

	# playlist_links = [playlist.playlist_uri for playlist in
	#                   PlaylistDetails.query.filter_by(user_id=user.id).all()]
	# if (playlist['followers']['total']) < 750:
	# 	return render_template('playlister_profile.html',
	# 												 name=current_user.first_name,
	# 												 too_short=True,
	# 												 playlist_dict=PlaylistDetails.query.filter_by(user_id=user.id).all())

	if PlaylistDetails.query.filter_by(playlist_uri=uri).first() is None:
		overall_genre = get_playlist_genre([track['track']['artists'][0]['uri']
		                                    for track in playlist['tracks']['items']], sp)
		playlist_details = PlaylistDetails(user.id, playlist['name'],
		                                   uri, playlist['followers']['total'],
		                                   len(playlist['tracks']['items']),
		                                   0, overall_genre)
		db.session.add(playlist_details)
		db.session.commit()

		for track in playlist['tracks']['items']:
			artist_name = track['track']['artists'][0]['name']
			p_id = PlaylistDetails.query.filter_by(playlist_uri=uri).first().id
			artist_in_playlist = ArtistsInPlaylist(p_id, artist_name=re.sub('[^A-Za-z0-9]+', ' ', artist_name))
			db.session.add(artist_in_playlist)
			db.session.commit()
	else:
		return render_template('playlister_profile.html',
		                       name=current_user.first_name,
		                       already_added=True,
		                       playlist_dict=PlaylistDetails.query.filter_by(user_id=user.id).all())
	return render_template('playlister_profile.html',
	                       name=current_user.first_name,
	                       too_short=False,
	                       playlist_dict=PlaylistDetails.query.filter_by(
		                       user_id=user.id).all())


@main.route('/artist_profile')
@login_required
def artist_profile():
	user = Users.query.filter_by(email=current_user.email).first()
	sp = refresh_access_token(SpotifyToken.query.filter_by(user_id=user.id).first().refresh_token, user.id)

	sim_artists = SimilarArtists.query.filter_by(artist_id=user.id).first()
	sim_artists = [sim_artists.similar_artist_1, sim_artists.similar_artist_2, sim_artists.similar_artist_3,
	               sim_artists.similar_artist_4, sim_artists.similar_artist_5]
	all_artists = sp.artists(sim_artists)['artists']

	genres = [artist['genres'] for artist in all_artists]
	genres = [genre for sublist in genres for genre in sublist]

	similar_playlists = PlaylistDetails.query.filter(PlaylistDetails.genre.in_(genres)).all()
	similar_playlist_ids = [playlist.playlist_uri.split(':')[2] for playlist in similar_playlists]
	playlist_embed_urls = ["https://open.spotify.com/embed/playlist/%s" % p_id for p_id in similar_playlist_ids]

	return render_template('artist_profile.html',
	                       user_name=user.first_name,
	                       playlist_embed_urls=playlist_embed_urls,
	                       tracks=get_curr_artist_tracks(user.id),
	                       user_credits=user.credits if user.credits is not None else 0,
	                       credits_info=credits_info, playlist_dict=similar_playlists,
	                       related_artists=get_curr_sim_artists(user.id, sp))


@main.route('/artist_profile_update', methods=['POST'])
@login_required
def artist_song():
	user = Users.query.filter_by(email=current_user.email).first()
	sp = refresh_access_token(SpotifyToken.query.filter_by(user_id=user.id).first().refresh_token, user.id)

	if request.form.get('payment_success'):
		flash('Payment success!')
		return redirect(url_for('main.artist_profile'))

	song_uri = request.form.get('song_uri')
	uploaded_artist_uris = [request.form.get('similar_artist1_uri'), request.form.get('similar_artist2_uri'),
	                        request.form.get('similar_artist3_uri'), request.form.get('similar_artist4_uri'),
	                        request.form.get('similar_artist5_uri')]
	song_description = request.form.get('song_description') if request.form.get('song_description') is not None else ""

	try:
		song_details = sp.track(song_uri)
	except spotipy.client.SpotifyException as e:
		flash("There was an issue retrieving your requested track from Spotify, please \
           check your URI, make sure it is a track link not an album one and try again")
		return redirect(url_for('main.artist_profile'))

	try:
		all_artists = sp.artists(uploaded_artist_uris)['artists']
	except spotipy.client.SpotifyException as e:
		flash("There was an issue retrieving your similar artists from Spotify, "
		      "please make sure your URIs are correct and try again.")
		return redirect(url_for('main.artist_profile'))

	new_track = ArtistTracks(user.id, song_details['name'], song_description,
	                         song_details['external_urls']['spotify'], song_uri, None)
	db.session.add(new_track)
	db.session.commit()

	if SimilarArtists.query.filter_by(artist_id=user.id).first() is None:
		similar_artists = SimilarArtists(user.id,
		                                 request.form.get('similar_artist1_uri'),
		                                 request.form.get('similar_artist2_uri'),
		                                 request.form.get('similar_artist3_uri'),
		                                 request.form.get('similar_artist4_uri'),
		                                 request.form.get('similar_artist5_uri'))
		db.session.add(similar_artists)
	else:
		sim_artists = SimilarArtists.query.filter_by(artist_id=user.id).first()
		sim_artists = [sim_artists.similar_artist_1, sim_artists.similar_artist_2, sim_artists.similar_artist_3,
		               sim_artists.similar_artist_4, sim_artists.similar_artist_5]
		intersection_artists = []
		for old, new in zip(sim_artists, uploaded_artist_uris):
			if new is None or old == new:
				intersection_artists.append(old)
			elif old != new:
				intersection_artists.append(new)
		curr_sim_artists = SimilarArtists.query.filter_by(artist_id=user.id).first()
		curr_sim_artists.similar_artist_1 = intersection_artists[0]
		curr_sim_artists.similar_artist_2 = intersection_artists[0]
		curr_sim_artists.similar_artist_3 = intersection_artists[0]
		curr_sim_artists.similar_artist_4 = intersection_artists[0]
		curr_sim_artists.similar_artist_5 = intersection_artists[0]
	db.session.commit()

	return redirect(url_for('main.artist_profile'))


@main.route('/song_to_plist', methods=['POST'])
@login_required
def add_song_to_playlist():
	try:
		user = Users.query.filter_by(email=current_user.email).first()
		plist_id = request.args.get('plist_id')
		song_to_add_uri = request.args.get('song_id')
		song_db_data = ArtistTracks.query.filter_by(track_uri=song_to_add_uri).first()
		song_db_data.placed_playlist_id = int(plist_id)

		user.credits = user.credits - 1

		playlist = PlaylistDetails.query.filter_by(id=plist_id).first()
		playlist.placement_rate += 1
		db.session.commit()

		playlist_user_id = playlist.user_id
		spotify_login = SpotifyToken.query.filter_by(user_id=playlist_user_id).first()
		sp = refresh_access_token(SpotifyToken.query.filter_by(user_id=playlist_user_id).first().refresh_token,
		                          playlist_user_id)
		sp.user_playlist_add_tracks(user=spotify_login.spotify_user_id, playlist_id=str(playlist.playlist_uri),
		                            tracks=[song_to_add_uri])

		return json.dumps({'success': True}), 200
	except Exception as e:
		return json.dumps({'fail': e}), 500
