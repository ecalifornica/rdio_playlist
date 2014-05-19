import logging
import os
from rdio import Rdio
import pymongo
import flask
from flask_login import LoginManager, login_user, current_user, logout_user
import lib

with open('playlist.log', 'w'):
    pass
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('playlist.log')
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.debug('\nPlaylist start')
app = flask.Flask(__name__)
app.config['SECRET_KEY'] = os.environ['FLASK_SECRET_KEY']
CONSUMER_SECRET = os.environ['RDIO_SECRET']
CONSUMER_KEY = os.environ['RDIO_KEY']
#on_heroku = False
db, OAUTH_CALLBACK_URL = lib.db_setup(app)
rdio_oauth_tokens = db.oauth_tokens
oauth_temp_db = db.temp_tokens
login_manager = LoginManager()
login_manager.init_app(app)


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


@app.route('/', methods=['GET', 'POST'])
def index():
    playlist_url = None
    artists=[]
    if current_user.is_authenticated():
        sign_in = False
        user = rdio_oauth_tokens.find_one({'user_key': current_user.get_id()})
        user_name = user['user_name']
        user_key = user['user_key']
        token = tuple(user['token'])
        rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), token)
        logger.debug('{} ({}) is authenticated'.format(user_name, user_key))
    else:
        sign_in = True
        user_name = None
    if flask.request.method == 'POST':
        logger.debug('Method: POST, user: {}'.format(user_name))
        if 'signin' in flask.request.form.keys():
            logger.debug('Signing in')
            rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET))
            auth_url = rdio.begin_authentication(OAUTH_CALLBACK_URL)
            session_id = flask.request.cookies['session']
            inserted_temp_token = oauth_temp_db.insert({'oauth token': rdio.token[0], 'oauth_dance_token': rdio.token})
            logger.debug('inserted token: {}'.format(inserted_temp_token))
            logger.debug('Redirecting to Rdio oauth')
            return flask.redirect(auth_url)
        if 'artistname' in flask.request.form.keys():
            search_artist = flask.request.form['artistname']
            artists = lib.create_artist_list(search_artist, rdio)
        if 'create playlist' in flask.request.form.keys():
            token = tuple(rdio_oauth_tokens.find_one(
                {'user_key': current_user.get_id()})['token'])
            playlist_url = lib.create_rdio_playlist(token, flask.request)
            return flask.redirect('http://rdio.com{}'.format(playlist_url))
        if 'logout' in flask.request.form.keys():
            logout_user()
            logger.debug('User logged out.')
            return flask.redirect('/')
    if flask.request.method == 'GET':
        logger.debug('Method: GET')
        if 'oauth_token' in flask.request.args.keys():
            logger.debug('Oauth callback.')
            access_token = lib.rdio_access_token(flask.request, oauth_temp_db)
            rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), access_token)
            user = rdio.call("currentUser")['result']
            user_key, user_name = user['key'], user['firstName']
            if rdio_oauth_tokens.find_one({'user_key': user_key}) is None:
                logger.debug('User not in database, inserting:')
                logger.debug(rdio_oauth_tokens.insert({'user_key': user_key,
                                                'token': rdio.token,
                                                'user_name': user_name}))
            else:
                logger.debug('User found in database.')
                pass
            session_user = FlaskLoginUser(user_key)
            logger.debug('Logging in: {}'.format(session_user))
            login_user(session_user)
            flask.session['logged_in'] = True
            sign_in = False
            return flask.redirect('/')
    return flask.render_template('index.html', artists=artists, sign_in=sign_in,
                           user_name=user_name, playlist_url=playlist_url)


if __name__ == '__main__':
    app.run(host='blametommy.com')
