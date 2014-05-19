import logging
import os
import flask
import flask_login
from rdio import Rdio
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('playlist.log')
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
CONSUMER_SECRET = os.environ['RDIO_SECRET']
CONSUMER_KEY = os.environ['RDIO_KEY']


def rdio_access_token(request=None, oauth_temp_db=None):
    callback_token = request.args.get('oauth_token')
    callback_verifier = request.args.get('oauth_verifier')
    oauth_dance_token = oauth_temp_db.find_one({'oauth token': callback_token}) 
    oauth_dance_token = oauth_dance_token['oauth_dance_token']
    rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), oauth_dance_token)
    rdio.complete_authentication(callback_verifier)
    access_token = rdio.token
    return access_token

def create_rdio_playlist(token, request):
    logger.debug('Creating playlist')
    rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), token)
    artist_key = request.form['create playlist']
    search = rdio.call('get', {'keys': artist_key})
    artist = search['result'][artist_key]['name']
    artist_top_ten_tracks = rdio.call('getTracksForArtist',
                                      {'artist': artist_key})
    if len(artist_top_ten_tracks['result']) == 0:
        # Flash message instead.
        return 'could not find any tracks'
    api_call_key_list = []
    for track in artist_top_ten_tracks['result']:
        api_call_key_list.append(track['key'])
    playlist = ','.join(api_call_key_list)
    created_playlist = rdio.call('createPlaylist', {
        'name': '{}\'s Top Ten'.format(artist),
        'description': 'Top ten tracks by play count',
        'tracks': playlist})
    playlist_url = created_playlist['result']['url']
    #user = rdio_oauth_tokens.find_one({'user_key': current_user.get_id()})
    logger.debug('Playlist created successfully.') 
    return playlist_url
    
