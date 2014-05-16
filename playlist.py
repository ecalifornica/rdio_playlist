import logging
import os
from rdio import Rdio
import pymongo
from flask import (Flask, session, render_template, request, redirect)
from flask_login import LoginManager, login_user, current_user, logout_user
with open('playlist.log', 'w'):
    pass
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('playlist.log')
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.debug('\nPlaylist start')
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['FLASK_SECRET_KEY']
CONSUMER_SECRET = os.environ['RDIO_SECRET']
CONSUMER_KEY = os.environ['RDIO_KEY']
on_heroku = False
if 'ON_HEROKU' in os.environ:
    logger.debug('Running on Heroku production environment')
    on_heroku = True
    app.config['DEBUG'] = False
    OAUTH_CALLBACK_URL = 'http://rdiotopten.com/'
    MONGO_URL = os.environ.get('MONGOHQ_URL')
    logger.debug('MONGO_URL: {}'.format(MONGO_URL))
    dbclient = pymongo.MongoClient(MONGO_URL)
    # Do this without hardcoding?
    db = dbclient.app25053168
else:
    app.config['DEBUG'] = True
    logger.debug('Running in development environment')
    OAUTH_CALLBACK_URL = 'http://blametommy.com:5000'
    dbclient = pymongo.MongoClient()
    db = dbclient.top_tracks
rdio_oauth_tokens = db.oauth_tokens
login_manager = LoginManager()
login_manager.init_app(app)


class OauthPlaceholder(object):
    def __init__(self):
        self.oauth_token = None
        self.access_token = None
        self.userid = None


class FlaskLoginUser():
    def __init__(self, userid):
        self.id = userid

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User {}>'.format(self.id)


@login_manager.user_loader
def load_user(userid):
    return FlaskLoginUser(userid)


oauth_dancer = OauthPlaceholder()


@app.route('/', methods=['GET', 'POST'])
def index():
    logger.debug('Index route')
    #print('is authenticated: {}'.format(current_user.is_authenticated()))
    playlist_url = None
    artists=[]
    playlists=[]
    if current_user.is_authenticated():
        sign_in = False
        user = rdio_oauth_tokens.find_one({'user_key': current_user.get_id()})
        user_icon = user['user_icon']
        user_name = user['user_name']
        user_key = user['user_key']
        token = tuple(user['token'])
        rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), token)
        logger.debug('{} ({}) is authenticated'.format(user_name, user_key))
    else:
        sign_in = True
        user_icon = None
        user_name = None
    if request.method == 'POST':
        logger.debug('Method: POST, user: {}'.format(user_name))
        if 'signin' in request.form.keys():
            logger.debug('Sign in')
            rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET))
            auth_url = rdio.begin_authentication(OAUTH_CALLBACK_URL)
            oauth_dancer.oauth_token = rdio.token
            return redirect(auth_url)
        if 'artistname' in request.form.keys():
            logger.debug('artist name')
            token = tuple(user['token'])
            rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), token)
            search_artist = request.form['artistname']
            search_result = rdio.call('search',
                                      {'query': search_artist,
                                       'types': 'Artist'})
            search_result = search_result['result']['results']
            logger.debug(search_result)
            artists = []
            for artist in search_result:
                if artist['length'] > 0:
                    logger.debug(artist['length'])
                artists.append({
                    'name': artist['name'],
                    'url': artist['shortUrl'],
                    'key': artist['key']})
        if 'create playlist' in request.form.keys():
            logger.debug('create playlist')
            token = tuple(rdio_oauth_tokens.find_one(
                {'user_key': current_user.get_id()})['token'])
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
            return redirect('http://rdio.com{}'.format(playlist_url))
        if 'logout' in request.form.keys():
            logout_user()
            logger.debug('User logged out.')
            return redirect('/')
    if request.method == 'GET':
        logger.debug('Method: GET')
        '''
        if current_user.is_authenticated():
            logger.debug('User {} is authenticated.'.format(user['user_key']))
            token = tuple(user['token'])
            rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), token)
            sign_in = False
        '''
        if 'oauth_token' in request.args.keys():
            logger.debug('Oauth callback.')
            rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET),
                        oauth_dancer.oauth_token)
            rdio.complete_authentication(request.args.get('oauth_verifier'))
            oauth_dancer.access_token = rdio.token
            rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), rdio.token)
            user = rdio.call("currentUser")['result']
            user_key, user_icon, user_name = user['key'], user['icon'], user['firstName']
            if rdio_oauth_tokens.find_one({'user_key': user_key}) is None:
                logger.debug('User not in database, inserting:')
                logger.debug(rdio_oauth_tokens.insert({'user_key': user_key,
                                                'token': rdio.token,
                                                'user_icon': user_icon,
                                                'user_name': user_name}))
            else:
                logger.debug('User found in database.')
                pass
            session_user = FlaskLoginUser(user_key)
            logger.debug('Logging in: {}'.format(session_user))
            login_user(session_user)
            session['logged_in'] = True
            sign_in = False
            return redirect('/')
    return render_template('index.html', artists=artists, sign_in=sign_in, user_icon=user_icon,
                           user_name=user_name, playlist_url=playlist_url)



if __name__ == '__main__':
    app.run(host='blametommy.com')
