# main.py

from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from .models import Users, PlaylistUri
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

client_creds = SpotifyClientCredentials()
sp = spotipy.Spotify(client_credentials_manager=client_creds)

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/profile')
@login_required
def profile():
    if current_user.user_type == 1:
        user = Users.query.filter_by(email=current_user.email).first()
        playlist_links = PlaylistUri.query.filter_by(user_id=user.id).all()
        return render_template('playlister_profile.html', name=current_user.first_name,
                                playlist_links=playlist_links)
    elif current_user.user_type == 2:
        return render_template('artist_profile.html', name=current_user.first_name)

@main.route('/check_playlist', methods=['POST'])
@login_required
def check_playlist():
    playlists = sp.user_playlists('spotify')
    print(playlists)
    return redirect(url_for('main.profile'))
        
    
    
