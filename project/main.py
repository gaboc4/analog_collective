import json
import re
import spotipy
import os
import stripe
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

import smtplib
from .models import Users, PlaylistDetails, SpotifyToken, ArtistsInPlaylist, \
	ArtistTracks, SimilarArtists, PlaylistToPlacedSong, BlogPosts
from . import db
from .helpers import refresh_access_token, get_access_and_refresh, \
	get_playlist_genre, get_curr_artist_tracks, get_curr_sim_artists, refresh_playlist_deets


main = Blueprint('main', __name__)


credits_info = "These tokens represent how much money you have put " \
               "into the platform in order to add your songs to a playlist. " \
               "You can add more to your account from the Store page!"


@main.route('/')
@main.route('/index')
def index():
	return render_template('index.html')


@main.route('/contact_form', methods=['POST'])
def contact_form():
	try:
		smtp_obj = smtplib.SMTP_SSL('smtpout.secureserver.net', 465)
		smtp_obj.ehlo()
		smtp_obj.login(os.environ['EMAIL_ACCT'], os.environ['EMAIL_PASS'])
		message = 'Subject: {}\n\n{}'.format('Analog Collective Contact Form',
		                                     str(request.form.get('contact_msg')))
		smtp_obj.sendmail(request.form.get('contact_email'), "will@analogcollective.com",
		                  message)
		flash("Thank you we will be in touch shortly!")
		return redirect(url_for('main.index'))
	except Exception as e:
		print(e)
		flash('There was an issue sending your message. Please try again '
		      'or email will@analogcollective.com directly.')
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
		return redirect(url_for('main.playlister_profile'))
	elif user.user_type == 2:
		return redirect(url_for('main.artist_profile'))


@main.route('/stripe_auth')
@login_required
def stripe_auth():
	user = Users.query.filter_by(email=current_user.email).first()
	code = request.args.get('code')
	stripe.api_key = os.environ['STRIPE_SK']

	if code:
		response = stripe.OAuth.token(
			grant_type='authorization_code',
			code=code,
		)

		# Access the connected account id in the response
		connected_account_id = response['stripe_user_id']
		user.payment_info = connected_account_id
		db.session.commit()
		flash('Payment account creation successful!')
		if user.user_type == 1:
			return redirect(url_for('main.playlister_profile'))
		elif user.user_type == 2:
			return redirect(url_for('main.artist_profile'))
	flash('Payment account creation not successful please try again')
	if user.user_type == 1:
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

	if user.payment_info is None:
		return render_template('playlister_profile.html', name=current_user.first_name, playlist_dict=playlist_dict,
		                       stripe_signup="https://connect.stripe.com/express/oauth/authorize?redirect_uri="
		                                     "http://127.0.0.1:5000/stripe_auth&client_id="
		                                     "ca_Gk2G8OaZ5AwgppO4z4aUVv3OHPsBs18T&state=12345",
		                       approval_needed=True)

	stripe_account_link = stripe.Account.create_login_link(user.payment_info)['url']
	return render_template('playlister_profile.html', name=current_user.first_name, playlist_dict=playlist_dict,
	                       stripe_account_link=stripe_account_link)


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

	if (playlist['followers']['total']) < 750:
		return render_template('playlister_profile.html', name=current_user.first_name, too_short=True,
		                       playlist_dict=PlaylistDetails.query.filter_by(user_id=user.id).all())

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
		return render_template('playlister_profile.html', name=current_user.first_name, already_added=True,
		                       playlist_dict=PlaylistDetails.query.filter_by(user_id=user.id).all())
	return redirect(url_for('main.playlister_profile'))


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

	if user.payment_info is None:
		return render_template('artist_profile.html',
		                       user_name=user.first_name, approval_needed=True,
		                       playlist_embed_urls=playlist_embed_urls,
		                       tracks=get_curr_artist_tracks(user.id),
		                       user_credits=user.credits if user.credits is not None else 0,
		                       credits_info=credits_info, playlist_dict=similar_playlists,
		                       related_artists=get_curr_sim_artists(user.id, sp))

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

	if song_uri != '':
		try:
			song_details = sp.track(song_uri)
			new_track = ArtistTracks(user.id, song_details['name'], song_description,
			                         song_details['external_urls']['spotify'], song_uri)
			db.session.add(new_track)
			db.session.commit()
		except spotipy.client.SpotifyException as e:
			flash("There was an issue retrieving your requested track from Spotify, please \
	           check your URI, make sure it is a track link not an album one and try again")
			return redirect(url_for('main.artist_profile'))

	try:
		if len([x for x in uploaded_artist_uris if x != '']) != 0:
			all_artists = sp.artists([x for x in uploaded_artist_uris if x != ''])['artists']
	except spotipy.client.SpotifyException as e:
		flash("There was an issue retrieving your similar artists from Spotify, "
		      "please make sure your URIs are correct and try again.")
		return redirect(url_for('main.artist_profile'))

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
		if len(uploaded_artist_uris) != len(sim_artists):
			for i in range(len(sim_artists) - len(uploaded_artist_uris) + 1):
				uploaded_artist_uris.append('')
		for old, new in zip(sim_artists, uploaded_artist_uris):
			if new == '' or old == new:
				intersection_artists.append(old)
			elif old != new:
				intersection_artists.append(new)
		curr_sim_artists = SimilarArtists.query.filter_by(artist_id=user.id).first()
		curr_sim_artists.similar_artist_1 = intersection_artists[0]
		curr_sim_artists.similar_artist_2 = intersection_artists[1]
		curr_sim_artists.similar_artist_3 = intersection_artists[2]
		curr_sim_artists.similar_artist_4 = intersection_artists[3]
		curr_sim_artists.similar_artist_5 = intersection_artists[4]
	db.session.commit()

	return redirect(url_for('main.artist_profile'))


@main.route('/song_to_plist', methods=['POST'])
@login_required
def add_song_to_playlist():
	try:
		user = Users.query.filter_by(email=current_user.email).first()
		plist_id = request.args.get('plist_id')
		song_to_add_uri = request.args.get('song_id')

		# Alter database section ---------------------------------------
		user.credits = user.credits - 1

		playlist = PlaylistDetails.query.filter_by(id=plist_id).first()
		playlist.placement_rate += 1

		song_db_data = ArtistTracks.query.filter_by(track_uri=song_to_add_uri).order_by(ArtistTracks.id.desc()).first()

		song_to_playlist = PlaylistToPlacedSong(playlist_id=playlist.id, song_id=song_db_data.id)
		db.session.add(song_to_playlist)

		playlister = Users.query.filter_by(id=playlist.user_id).first()

		if 1000 < playlist.num_followers < 5000:
			pmt_amnt = 300
		elif 5000 < playlist.num_followers < 20000:
			pmt_amnt = 600
		elif 20000 < playlist.num_followers:
			pmt_amnt = 900

		if stripe.Balance.retrieve()['available'][0]['amount'] <= pmt_amnt:
			charge_to_tie_to = stripe.Charge.list(limit=3)['data'][0]['id']

			transfer = stripe.Transfer.create(
				amount=5000,
				currency='usd',
				destination=playlister.payment_info,
				source_transaction=charge_to_tie_to,
			)
		else:
			transfer = stripe.Transfer.create(
				amount=5000,
				currency='usd',
				destination=playlister.payment_info
			)

		db.session.commit()
		# ---------------------------------------------------------------

		spotify_login = SpotifyToken.query.filter_by(user_id=playlist.user_id).first()
		sp = refresh_access_token(SpotifyToken.query.filter_by(user_id=playlist.user_id).first().refresh_token,
		                          playlist.user_id)
		sp.user_playlist_add_tracks(user=spotify_login.spotify_user_id, playlist_id=str(playlist.playlist_uri),
		                            tracks=[song_to_add_uri])

		refresh_playlist_deets(playlist.playlist_uri, sp)

		return json.dumps({'success': True}), 200
	except Exception as e:
		return json.dumps({'fail': e}), 500


@main.route('/blog')
@login_required
def blog():
	posts = BlogPosts.query.all()
	return render_template('blog.html', posts=posts, user_email=current_user.email)


@main.route('/blog', methods=['POST'])
@login_required
def blog_post():
	if current_user.email == "will@analogcollective.com":
		title = request.form.get('post_title')
		content = request.form.get('post_content')
		new_post = BlogPosts(title=title, date=datetime.now().strftime('%Y-%m-%d'), content=content)
		db.session.add(new_post)
		db.session.commit()
		return redirect(url_for('main.blog'))
	return redirect(url_for('main.blog'))
