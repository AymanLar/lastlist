from flask import Flask, request, redirect, session, url_for, render_template
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.config['SESSION_COOKIE_NAME'] = 'spotify-login-session'

# Spotify API credentials
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SCOPE = "playlist-modify-public"

# Spotipy object for Spotify API calls
sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                        client_secret=SPOTIPY_CLIENT_SECRET,
                        redirect_uri=SPOTIPY_REDIRECT_URI,
                        scope=SCOPE)

@app.route('/')
def index():
    return render_template('index.html')

# Route to login to Spotify
@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

# Spotify OAuth callback
@app.route('/callback')
def callback():
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)

    if not token_info:
        return redirect(url_for('login'))
    
    session["token_info"] = token_info
    return redirect('/lastfm_user')

# Last.fm username input route
@app.route('/lastfm', methods=['POST'])
def lastfm():
    session['lastfm_username'] = request.form.get('username')
    session['lastfm_list'] = request.form.get('what')
    return redirect(url_for('playlist'))

# Route to display Last.fm username input form
@app.route('/lastfm_user')
def lastfm_input():
    return render_template('lastfm.html')

# Route to generate playlist
@app.route('/playlist')
def playlist():
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('login'))

    sp = spotipy.Spotify(auth=token_info['access_token'])
    lastfm_username = session.get('lastfm_username', None)
    lastfm_list = session.get('lastfm_list')

    recommended_tracks = get_lastfm_recommendations(lastfm_username,lastfm_list)

    # Create a new playlist
    user_id = sp.current_user()['id']
    playlist_name = f"{lastfm_username}'s {lastfm_list.capitalize()} Tracks"
    playlist = sp.user_playlist_create(user_id, playlist_name)

    # Search and add tracks to playlist
    track_uris = []
    for track in recommended_tracks:
        track_name = track['name']
        artist_name = track['artist']
        track_uri = search_spotify_track(sp, track_name, artist_name)
        if track_uri:
            track_uris.append(track_uri)

    # Add tracks to Spotify playlist
    if track_uris:
        sp.playlist_add_items(playlist['id'], track_uris)

    return render_template('playlist.html', playlist_name=playlist_name, tracks=recommended_tracks)

# Helper function to get Last.fm recommendations
def get_lastfm_recommendations(username,what):
    url = f"https://www.last.fm/player/station/user/{username}/{what}/"
    response = requests.get(url)
    data = response.json()

    # Extract tracks from the Last.fm response
    tracks = []
    for track in data['playlist']:
        tracks.append({
            'name': track['name'],
            'artist': track['artists'][0]['name']
        })
    return tracks

def search_spotify_track(sp, track_name, artist_name):
    query = f"track:{track_name} artist:{artist_name}"
    results = sp.search(q=query, type='track', limit=1)
    if results['tracks']['items']:
        return results['tracks']['items'][0]['uri']
    return None

if __name__ == '__main__':
    app.run(debug=True)

