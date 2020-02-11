from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from .models import Users, PlaylistDetails, SpotifyToken, ArtistsInPlaylist, \
    ArtistTracks, SimilarArtists
from . import db
from .main import tokens_info
from .helpers import refresh_access_token, \
    get_curr_sim_artists, get_curr_artist_tracks
import spotipy
import sys
import os
import stripe
import json

payment = Blueprint('payment', __name__)

stripe.api_key = os.environ['STRIPE_KEY']


@payment.route('/shop/', methods=['GET', 'POST'])
@login_required
def submit_payment():
    user = Users.query.filter_by(email=current_user.email).first()
    tokens = user.tokens if user.tokens is not None else 0
    if request.method == 'GET':
        return render_template('shop.html',
                               tokens=tokens, error='',
                               user_name=user.first_name + " " + user.last_name)
    elif request.method == "POST":
        data = request.get_json()
        try:
            # Create the PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=data['price'],
                currency='usd',
                payment_method=data['payment_method_id'],
                confirm=True,
                error_on_requires_action=True,
            )
            return generate_response(intent, data['price'])
        except stripe.error.CardError as e:
            return json.dumps({'error': e.user_message}), 200


def generate_response(intent, price):
    if intent.status == 'succeeded':
        user = Users.query.filter_by(email=current_user.email).first()
        user.tokens = price / 10
        db.session.commit()
        return json.dumps({'sucess': True}), 200
    else:
        # Any other status would be unexpected, so error
        return json.dumps({'error': 'Invalid PaymentIntent status'}), 500
