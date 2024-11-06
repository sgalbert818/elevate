from flask import Flask, redirect, jsonify, session, request
import requests
import urllib.parse
import datetime
from flask_cors import CORS  # Import CORS
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from collections import Counter
import math
import random
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize the Flask application
application = Flask(__name__)

# Set up allowed origins dynamically based on the environment
frontend_origin = "amplify url"  # Keep localhost for testing
frontend_test = "http://localhost:5173"  # Keep localhost for testing
backend_origin = "http://18.218.68.142:5001"  # Your EC2 production IP

# Configure CORS for the application
CORS(application, resources={r"/*": {"origins": [frontend_test, backend_origin]}}, supports_credentials=True)

application.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # Ensure this key is set and remains consistent
application.config['SESSION_COOKIE_SECURE'] = True  # Set to False for local development if using HTTP
application.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Or 'None' if using secure cross-site cookies
application.config['SESSION_PERMANENT'] = False  # Consider disabling permanent sessions if you only need temporary data


CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

keywords = {
    'workout': [
        'workout', 'exercise', 'gym', 'fitness',
        'cardio', 'run', 'strength', 'sweat', 'lift'
    ],
    'relaxation': [
        'relaxation', 'chill', 'calm', 'soothing', 
        'unwind', 'peaceful', 'meditation', 'mindfulness'
    ],
    'road_trip': [
        'road trip', 'travel', 'journey', 'adventure', 
        'driving', 'cruising', 'highway'
    ],
    'party': [
        'party', 'celebration', 'dance', 'upbeat', 
        'club', 'fun', 'pregame', 'bangers'
    ],
    'focus': [
        'focus', 'study', 'concentration', 'productivity', 
        'background music', 'ambient', 'reading'
    ],
    'cooking': [
        'cooking', 'kitchen', 'culinary'
    ],
    'cleaning': [
        'cleaning', 'tidy', 'chores', 'organization', 
        'declutter', 'productive', 'motivational'
    ],
    'date_night': [
        'romantic', 'love', 'dinner', 'candlelight'
    ]
}
target_features = {
    'workout': "min_energy={energy}&min_tempo={tempo}&min_danceability={danceability}&min_valence={valence}",
    'relaxation': "min_acousticness={acousticness}&min_valence={valence}&max_energy={energy}&max_tempo={tempo}",
    'roadtrip': "target_energy={energy}&target_danceability={danceability}&target_tempo={tempo}",
    'party': "min_energy={energy}&min_danceability={danceability}&min_valence={valence}",
    'focus': "min_acousticness={acousticness}&max_energy={energy}",
    'cooking': "target_energy={energy}&target_tempo={tempo}&target_valence={valence}",
    'cleaning': "min_energy={energy}&min_tempo={tempo}&min_danceability={danceability}",
    'datenight': "min_acousticness={acousticness}&min_valence={valence}&max_tempo={tempo}&max_energy={energy}"
}

credentials = {} # use credentials global object in place of session for demo version

# API ENDPOINTS


@application.route('/ping')
def ping():
    return jsonify('pong!')

@application.route('/login')
def login():
    try:
        scope = 'user-read-private user-read-email user-top-read playlist-modify-public playlist-modify-private' # permissions needed
        params = {
            'client_id': CLIENT_ID,
            'response_type': 'code',
            'scope': scope,
            'redirect_uri': REDIRECT_URI,
            'show_dialog': True # forces login every time if true
        }
        auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
        return redirect(auth_url) # redirects to spotify login page
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"message": f'Login failed. {str(e)}'}), 500

# redirect user after successful spotify login
@application.route('/callback')
def callback():
    try:
        if 'error' in request.args:
            raise ValueError(f"Spotify returned an error: {request.args['error']}")
        if 'code' not in request.args:
            raise ValueError("Authorization code not found in the request.")
            # build up request body with data to send to spotify to get access token
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        response = requests.post(TOKEN_URL, data=req_body)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch token")
        token_info = response.json()
        #session['access_token'] = token_info['access_token']
        #session['refresh_token'] = token_info['refresh_token']
        #session['expires_at'] = datetime.datetime.now().timestamp() + token_info['expires_in']
        global credentials  # Declare 'test' as global to modify it
        credentials['access_token'] = token_info['access_token']
        return redirect('http://localhost:5173/profile') # redirects to react app
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"message": f'Login failed. {str(e)}'}), 500
    
# pull user data upon successful login to build user 'profile'
@application.route('/profile', methods=['GET', 'OPTIONS'])
def profile():
    # Handle preflight requests
    '''if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        return add_cors_headers(response)'''
    try:
        # Check if the user is authenticated
        if 'access_token' not in credentials:
            print("Access token missing in credentials")
            return redirect('/login')
        
        headers = {'Authorization': f"Bearer {credentials.get('access_token')}"}
        endpoints = {
            'profile': 'me',  # Endpoint to get profile info
            'top_artists': 'me/top/artists',  # Get top artists
            'top_tracks': 'me/top/tracks'     # Get top tracks
        }

        # Call each endpoint sequentially
        profile_info = {}
        for key, endpoint in endpoints.items():
            response = requests.get(API_BASE_URL + endpoint, headers=headers)
            profile_info[key] = response.json()

        # Process retrieved data
        artist_ids = [artist['id'] for artist in profile_info['top_artists']['items']]
        track_ids = [track['id'] for track in profile_info['top_tracks']['items']]
        avg_audio_features = fetch_average_audio_features(track_ids)
        top_genres = fetch_top_genres(profile_info)

        # Save data in the session
        credentials['avg_audio_features'] = avg_audio_features  # Saves user average audio features
        credentials['top_artists'] = artist_ids                # Saves user top artists
        credentials['top_genres'] = top_genres                 # Saves user top genres
        credentials['user_id'] = profile_info['profile']['id']

        response = jsonify(profile_info)
        return add_cors_headers(response)
    
    except Exception as e:
        print(f"Error: {str(e)}")  # Print the exception message
        response = jsonify({"message": f"Unable to retrieve user profile. {str(e)}"})
    
# no refresh token since we are using credentials object instead of session
'''@application.route('/refresh-token')
def refresh_token():
    try:
        if 'refresh_token' not in session:
            return redirect('/login')
        if datetime.datetime.now().timestamp() > session['expires_at']: # session is expired, redirect to refresh token
            req_body = {
                'grant_type': 'refresh_token',
                'refresh_token': session['refresh_token'],
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
            }
            response = requests.post(TOKEN_URL, data=req_body) # generate new token
            new_token_info = response.json()
            session['access_token'] = new_token_info['access_token']
            session['expires_at'] = datetime.datetime.now().timestamp() + new_token_info['expires_in']
            return redirect('http://localhost:5173/profile')
    except Exception as e:
        print(f"Error: {str(e)}")  # Print the exception message
        return jsonify({"message": f"Unable to refresh authentication token. {str(e)}"}), 500'''
       
# logout/switch user
@application.route('/logout')
def logout():
    try:
        # session.clear() # clear session, redirect to login page
        credentials.clear()
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        print(f"Error: {str(e)}")  # Print the exception message
        return jsonify({"message": f"Logout failed. {str(e)}"}), 500

# builds new playlist for user on submit btn
@application.route('/recommendations', methods=['POST'])
def recommendations():
    try:
        if 'access_token' not in credentials:  # Check if the user is authenticated
            return redirect('/login')
        '''if datetime.datetime.now().timestamp() > session['expires_at']:  # Check if the access token is expired
            return redirect('/refresh-token')'''
        data = request.json
        activity = data.get('activity')  # selected activity from user on front end
        num_of_songs = 100
        playlist_keywords = keywords[activity]
        playlists = fetch_user_playlists()
        matching_playlists = [playlist['id'] for playlist in playlists if any(keyword in playlist['name'].lower() for keyword in playlist_keywords)]
        seed_artists, seed_genres = build_seed_arrays(matching_playlists, activity)
        recommendations = get_recommendations(seed_artists, seed_genres, num_of_songs, activity)
        response = jsonify(recommendations)
        return response
    except Exception as e:
        print(f"Error: {str(e)}")  # Print the exception message
        return jsonify({"message": f"Unable to get song recommendations. {str(e)}"}), 500
    
# once user is done adding/deleting songs, build playlist and send to spotify
@application.route('/build', methods=['POST'])
def build():
    try:
        if 'access_token' not in credentials:  # Check if the user is authenticated
            return redirect('/login')
        '''if datetime.datetime.now().timestamp() > session['expires_at']:  # Check if the access token is expired
            return redirect('/refresh-token')'''
        data = request.json
        playlist_name = data.get('name')
        playlist_songs = data.get('songs')
        res = ''
        playlist_id = create_spotify_playlist(playlist_name)
        if playlist_id:
            response = add_songs_to_playlist(playlist_id, playlist_songs)                
        return jsonify(response)
    except Exception as e:
        print(f"Error: {str(e)}")  # Print the exception message
        return jsonify({"message": f"Unable to build playlist. {str(e)}"}), 500


# HELPER FUNCTIONS


def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

def fetch_average_audio_features(track_ids): # finds and returns average audio features upon user login
    url = f"{API_BASE_URL}audio-features"
    headers = {'Authorization': f"Bearer {credentials.get('access_token')}"}
    params = {'ids': ','.join(track_ids)}
    response = requests.get(url, headers=headers, params=params)
    if not response.ok:
        raise ValueError(f"Failed to fetch audio features from Spotify API: {response.status_code} - {response.text}")
    audio_features = response.json().get('audio_features', [])
    data = []
    for feature in audio_features:
        if feature:  # Ensure feature is not None
            data.append({
                'acousticness': feature['acousticness'],
                'energy': feature['energy'],
                'valence': feature['valence'],
                'danceability': feature['danceability'],
                'tempo': feature['tempo']
            })
        else:
            raise ValueError(f"Unexpected response")
    df = pd.DataFrame(data)
    averages = {
        'acousticness': round(df['acousticness'].mean(), 2),
        'energy': round(df['energy'].mean(), 2),
        'valence': round(df['valence'].mean(), 2),
        'danceability': round(df['danceability'].mean(), 2),
        'tempo': round(df['tempo'].mean(), 2)
    }
    return averages # average audio features for user

def fetch_top_genres(profile_info, top_n=5):
    top_artists = profile_info.get("top_artists", {}).get("items", [])
    if not top_artists:
        raise ValueError(f"Failed to pull top genres from listener history")
    genre_counter = Counter()    
    for artist in top_artists:
        genres = artist.get("genres", []) # Get genres for each artist
        genre_counter.update(genres) # Update the counter with the artist's genres
    top_genres = genre_counter.most_common(top_n)
    return [genre for genre, count in top_genres] # return top genre for user

def build_seed_arrays(matching_playlists, activity):
    seed_artists = []  # We want 2 total (1 from user, 1 from popular)
    seed_genres = []   # We want 3 total (2 from user, 1 from popular)

    def add_unique_item(target_array, source_array):
        # Create a set of available items, excluding items already in target_array
        available_items = set(source_array) - set(target_array)
        if available_items:
            target_array.append(random.choice(list(available_items)))

    if matching_playlists:
        sample_playlist = random.choice(matching_playlists)
        top_artist_and_genre = get_top_artist_and_genre(sample_playlist)
        seed_artists.append(top_artist_and_genre['artist'])
        seed_genres.append(top_artist_and_genre['genre'])
    else:
        add_unique_item(seed_artists, credentials['top_artists'])
        add_unique_item(seed_genres, credentials['top_genres'])

    add_unique_item(seed_genres, credentials['top_genres'])

    # Select a unique popular artist and genre that aren't already in seeds
    while True:
        sample_popular_playlist = random_popular_playlist(activity)
        top_artist_and_genre = get_top_artist_and_genre(sample_popular_playlist)
        if top_artist_and_genre['artist'] not in seed_artists and top_artist_and_genre['genre'] not in seed_genres:
            break

    seed_artists.append(top_artist_and_genre['artist'])
    seed_genres.append(top_artist_and_genre['genre'])

    return seed_artists, seed_genres

def fetch_user_playlists(): # returns all user playlists
    url = f"{API_BASE_URL}me/playlists"
    headers = {'Authorization': f"Bearer {credentials.get('access_token')}"}
    response = requests.get(url, headers=headers)
    if not response.ok:
        raise ValueError(f"Failed to fetch user playlists for analysis")
    return response.json()['items']
    
from collections import Counter
import requests

def get_top_artist_and_genre(playlist_id):
    url = f"{API_BASE_URL}playlists/{playlist_id}/tracks"
    headers = {'Authorization': f"Bearer {credentials.get('access_token')}"}
    response = requests.get(url, headers=headers)
    if not response.ok:
        raise ValueError("Failed to analyze artist and genre information from playlists")
    tracks = response.json().get("items", [])
    if not tracks:
        raise ValueError("Could not find playlists to analyze")
    
    artist_count = Counter()
    genre_count = Counter()
    artist_ids = []

    for item in tracks:
        artist_id = item['track']['artists'][0]['id']
        artist_count[artist_id] += 1
        artist_ids.append(artist_id)

    # Fetch genres for all artists in a single request (up to 50 IDs at a time)
    unique_artist_ids = list(set(artist_ids))
    for i in range(0, len(unique_artist_ids), 20):
        batch_ids = unique_artist_ids[i:i+20]
        artist_url = f"https://api.spotify.com/v1/artists?ids={','.join(batch_ids)}"
        artist_response = requests.get(artist_url, headers=headers)
        if not artist_response.ok:
            raise ValueError("Failed to retrieve artist genre information")
        artists_info = artist_response.json().get("artists", [])
        for artist_info in artists_info:
            genre_count.update(artist_info.get("genres", []))

    # Determine top artist and top genre
    top_artist = artist_count.most_common(1)[0][0] if artist_count else None
    top_genre = genre_count.most_common(1)[0][0] if genre_count else None

    if not top_artist or not top_genre:
        raise ValueError("Failed to determine top artist/top genre")

    return {"artist": top_artist, "genre": top_genre}

def random_popular_playlist(search_term): # find random popular playlist related to selected activity
    url = f"{API_BASE_URL}search"
    params = {
        'q': search_term, # activity
        'type': 'playlist',  # search for playlists
        'limit': 20
    }
    headers = {'Authorization': f"Bearer {credentials.get('access_token')}"}
    response = requests.get(url, headers=headers, params=params)
    if not response.ok:
        raise ValueError(f"API response was not ok")        
    playlists = response.json().get('playlists', {}).get('items', [])
    if playlists:
        selected_playlist = random.choice(playlists)
        return selected_playlist['id']  # Return randomly selected playlist ID
    else:
        raise ValueError(f"No playlists found for analysis")
    
def get_recommendations(seed_artists, seed_genres, num_of_songs, activity): # returns recommended tracks
    base_url =  f'https://api.spotify.com/v1/recommendations?seed_artists={seed_artists[0]},{seed_artists[1]}&seed_genres={seed_genres[0]},{seed_genres[1]},{seed_genres[2]}&limit={num_of_songs}'
    activity_params = target_features.get(activity, "")
    formatted_params = activity_params.format(
        energy=credentials['avg_audio_features']['energy'],
        tempo=credentials['avg_audio_features']['tempo'],
        danceability=credentials['avg_audio_features']['danceability'],
        valence=credentials['avg_audio_features']['valence'],
        acousticness=credentials['avg_audio_features']['acousticness'],
    )
    url = f"{base_url}&{formatted_params}"
    headers = {'Authorization': f"Bearer {credentials.get('access_token')}"}
    response = requests.get(url, headers=headers)
    if not response.ok:
        raise ValueError(f"API response was not ok")
    recommendations = response.json().get('tracks', [])
    return recommendations

def create_spotify_playlist(playlist_name):
    url = f"{API_BASE_URL}users/{credentials['user_id']}/playlists"
    headers = {
        "Authorization": f"Bearer {credentials.get('access_token')}",
        "Content-Type": "application/json"
    }
    data = {
        "name": playlist_name,
        "description": "Created via the Spotify API",
        "public": False
    }
    response = requests.post(url, headers=headers, json=data)
    if not response.ok:
        raise ValueError(f"API response was not ok")
    return response.json()["id"]  # Playlist ID needed for the next step
    
def add_songs_to_playlist(playlist_id, track_uris):
    url = f"{API_BASE_URL}playlists/{playlist_id}/tracks"
    headers = {
        "Authorization": f"Bearer {credentials.get('access_token')}",
        "Content-Type": "application/json"
    }
    data = {
        "uris": track_uris  # Array of Spotify track URIs
    }
    response = requests.post(url, headers=headers, json=data)
    if not response.ok:
        raise ValueError(f"API response was not ok. Failed to add tracks to playlist")
    return("Tracks added successfully.")

# Run the application
if __name__ == "__main__":
    application.run(debug=True)