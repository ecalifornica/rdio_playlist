import logging
import os
import flask
import flask_login
from rdio import Rdio
import pymongo
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('playlist.log')
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
CONSUMER_SECRET = os.environ['RDIO_SECRET']
CONSUMER_KEY = os.environ['RDIO_KEY']


def rdio_access_token(request=None, oauth_temp_db=None):
    '''OAuth dance.'''
    callback_token = request.args.get('oauth_token')
    callback_verifier = request.args.get('oauth_verifier')
    oauth_dance_token = oauth_temp_db.find_one({'oauth token': callback_token}) 
    oauth_dance_token = oauth_dance_token['oauth_dance_token']
    rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), oauth_dance_token)
    rdio.complete_authentication(callback_verifier)
    access_token = rdio.token
    return access_token

def create_rdio_playlist(token, request):
    '''Rdio call, create playlist.'''
    logger.debug('Creating playlist')
    rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), token)
    artist_key = request.form['create playlist']
    search = rdio.call('get', {'keys': artist_key})
    artist = search['result'][artist_key]['name']
    artist_top_ten_tracks = rdio.call('getTracksForArtist',
                                      {'artist': artist_key})
    if len(artist_top_ten_tracks['result']) == 0:
        # Flash message instead.
        return 'Could not find any tracks. Click back to try another artist.'
    api_call_key_list = []
    for track in artist_top_ten_tracks['result']:
        api_call_key_list.append(track['key'])
    playlist = ','.join(api_call_key_list)
    created_playlist = rdio.call('createPlaylist', {
        'name': '{}\'s Top Ten'.format(artist),
        'description': 'Top ten tracks by play count',
        'tracks': playlist})
    playlist_url = created_playlist['result']['url']
    logger.debug('Playlist created successfully.\n') 
    return playlist_url
    

def create_artist_list(search_artist, rdio):
    '''Create a list of artists for user to choose from.'''
    logger.debug('Searching for {}'.format(search_artist))
    search_result = rdio.call('search',
                              {'query': search_artist,
                               'types': 'Artist'})
    search_result = search_result['result']['results']
    artists = []
    for artist in search_result:
        if artist['length'] > 0:
            artists.append({
                'name': artist['name'],
                'url': artist['shortUrl'],
                'key': artist['key']})
    return artists

def db_setup(app):
    if 'ON_HEROKU' in os.environ:
        logger.debug('Running on Heroku production environment')
        app.config['DEBUG'] = False
        OAUTH_CALLBACK_URL = 'http://rdiotopten.com/'
        MONGO_URL = os.environ.get('MONGOHQ_URL')
        logger.debug('MONGO_URL: {}'.format(MONGO_URL))
        dbclient = pymongo.MongoClient(MONGO_URL)
        # Remove hardcoding.
        db = dbclient.app25053168
        return db, OAUTH_CALLBACK_URL
    else:
        app.config['DEBUG'] = True
        logger.debug('Running in development environment')
        OAUTH_CALLBACK_URL = 'http://blametommy.com:5000'
        dbclient = pymongo.MongoClient()
        db = dbclient.top_tracks
        return db, OAUTH_CALLBACK_URL
