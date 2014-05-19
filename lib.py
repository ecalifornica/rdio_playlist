import logging
import os
import flask
import flask_login
# import rdio_oauth
from rdio import Rdio
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('playlist.log')
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
CONSUMER_SECRET = os.environ['RDIO_SECRET']
CONSUMER_KEY = os.environ['RDIO_KEY']

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


'''
@login_manager.user_loader
def load_user(userid):
    return FlaskLoginUser(userid)
'''

# Scope issues.
'''
def index_GET(Rdio, oauth_temp_db, rdio_oauth_tokens, sign_in, user_name, playlist_url, artists):
    logger.debug('Method: GET')
    if 'oauth_token' in flask.request.args.keys():
        logger.debug('Oauth callback.')
        # oauth_callback()
        oauth_token = flask.request.args['oauth_token']
        logger.debug('oauth token: {}'.format(oauth_token))
        oauth_dance_token = oauth_temp_db.find_one({'oauth token': oauth_token}) 
        oauth_dance_token = oauth_dance_token['oauth_dance_token']
        logger.debug('oauth_dance_token: {}'.format(oauth_dance_token))

        rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET),
                    oauth_dance_token)
        rdio.complete_authentication(flask.request.args.get('oauth_verifier'))
        #oauth_dancer.access_token = rdio.token
        rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), rdio.token)
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
        flask.session_user = FlaskLoginUser(user_key)
        logger.debug('Logging in: {}'.format(flask.session_user))
        flask_login.login_user(flask.session_user)
        flask.session['logged_in'] = True
        sign_in = False
        return flask.redirect('/')
    return flask.render_template('index.html', artists=artists, sign_in=sign_in, user_name=user_name, playlist_url=playlist_url)
'''

#def rdio_oauth(callback_token=None, callback_verifier=None, oauth_temp_db=None):
def rdio_access_token(request=None, oauth_temp_db=None):
    callback_token = request.args.get('oauth_token')
    callback_verifier = request.args.get('oauth_verifier')
    '''
    logger.debug('rdio_oauth method callback_token')
    logger.debug('callback verifier: {}'.format(callback_verifier))
    logger.debug('callback token: {}'.format(callback_token))
    '''
    oauth_dance_token = oauth_temp_db.find_one({'oauth token': callback_token}) 
    oauth_dance_token = oauth_dance_token['oauth_dance_token']
    # logger.debug('oauth_dance_token: {}'.format(oauth_dance_token))
    rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), oauth_dance_token)
    # logger.debug(rdio)
    rdio.complete_authentication(callback_verifier)
    access_token = rdio.token
    # rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), access_token)
    return access_token
