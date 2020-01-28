# models.py

from flask_login import UserMixin
from . import db

class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    first_name = db.Column(db.String(1000))
    last_name = db.Column(db.String(1000))
    email = db.Column(db.String(1000), unique=True)
    password = db.Column(db.String(1000))
    user_type = db.Column(db.Integer,  db.ForeignKey('user_type.id'))
    spot_auth = db.Column(db.Boolean)

class UserType(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))

class PlaylistDetails(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(1000))
    playlist_uri = db.Column(db.String(1000))
    num_followers = db.Column(db.Integer)
    num_tracks = db.Column(db.Integer)
    placement_rate = db.Column(db.Integer)

    def __init__(self, user_id, name, playlist_uri, num_followers, num_tracks, placement_rate):
        self.user_id = user_id
        self.name = name
        self.playlist_uri = playlist_uri
        self.num_followers = num_followers
        self.num_tracks = num_tracks
        self.placement_rate = placement_rate

class SpotifyToken(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    access_token = db.Column(db.String(1000))
    refresh_token = db.Column(db.String(1000))

    def __init__(self, user_id, access_token, refresh_token):
        self.user_id = user_id
        self.access_token = access_token
        self.refresh_token = refresh_token

class ArtistsInPlaylist(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer)
    artist_name = db.Column(db.String(1000))

    def __init__(self, playlist_id, artist_name):
        self.playlist_id = playlist_id
        self.artist_name = artist_name