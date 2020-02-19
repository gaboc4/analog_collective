# models.py
from datetime import datetime
from flask_login import UserMixin
from . import db


class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)  # primary keys are required by SQLAlchemy
    first_name = db.Column(db.String(1000))
    last_name = db.Column(db.String(1000))
    email = db.Column(db.String(1000), unique=True)
    password = db.Column(db.String(1000))
    user_type = db.Column(db.Integer, db.ForeignKey('user_type.id'))
    spot_auth = db.Column(db.Boolean)
    credits = db.Column(db.Integer)
    payment_info = db.Column(db.String(1000))
    stripe_approval_needed = db.Column(db.Boolean)

    def __init__(self, first_name, last_name, email, password, user_type):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password = password
        self.user_type = user_type
        self.spot_auth = False
        self.credits = 0


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
    genre = db.Column(db.String(1000))
    last_updated = db.Column(db.DateTime)

    def __init__(self, user_id, name, playlist_uri, num_followers, num_tracks, placement_rate,
                 genre):
        self.user_id = user_id
        self.name = name
        self.playlist_uri = playlist_uri
        self.num_followers = num_followers
        self.num_tracks = num_tracks
        self.placement_rate = placement_rate
        self.genre = genre
        self.last_updated = datetime.now()


class SpotifyToken(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    access_token = db.Column(db.String(1000))
    refresh_token = db.Column(db.String(1000))
    spotify_user_id = db.Column(db.String(1000))

    def __init__(self, user_id, access_token, refresh_token, spotify_user_id):
        self.user_id = user_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.spotify_user_id = spotify_user_id


class ArtistsInPlaylist(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer)
    artist_name = db.Column(db.String(1000))

    def __init__(self, playlist_id, artist_name):
        self.playlist_id = playlist_id
        self.artist_name = artist_name


class SimilarArtists(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    similar_artist_1 = db.Column(db.String(1000))
    similar_artist_2 = db.Column(db.String(1000))
    similar_artist_3 = db.Column(db.String(1000))
    similar_artist_4 = db.Column(db.String(1000))
    similar_artist_5 = db.Column(db.String(1000))

    def __init__(self, artist_id, similar_artist_1, similar_artist_2, similar_artist_3,
                 similar_artist_4, similar_artist_5):
        self.artist_id = artist_id
        self.similar_artist_1 = similar_artist_1
        self.similar_artist_2 = similar_artist_2
        self.similar_artist_3 = similar_artist_3
        self.similar_artist_4 = similar_artist_4
        self.similar_artist_5 = similar_artist_5


class ArtistTracks(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    track_name = db.Column(db.String(1000))
    track_summary = db.Column(db.String(1000))
    track_link = db.Column(db.String(1000))
    track_uri = db.Column(db.String(1000))
    placed_playlist_id = db.Column(db.Integer, db.ForeignKey('playlist_details.id'))

    def __init__(self, artist_id, track_name, track_summary, track_link, track_uri, placed_playlist_id):
        self.artist_id = artist_id
        self.track_name = track_name
        self.track_summary = track_summary
        self.track_link = track_link
        self.track_uri = track_uri
        self.placed_playlist_id = placed_playlist_id
