from flask import (Flask, session, render_template, request, redirect)
from flask_login import LoginManager, login_user, current_user
from rdio import Rdio
from pymongo import MongoClient
import os
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = os.environ['FLASK_SECRET_KEY']
CONSUMER_SECRET = os.environ['RDIO_SECRET']
CONSUMER_KEY = os.environ['RDIO_KEY']
dbclient = MongoClient()
db = dbclient.top_tracks
rdio_oauth_tokens = db.oauth_tokens
login_manager = LoginManager()
login_manager.init_app(app)


class oauth_placeholder(object):
    def __init__(self):
        self.oauth_token = None
        self.access_token = None
        self.userid = None


class flask_login_user():
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
    return flask_login_user(userid)


oauth_dancer = oauth_placeholder()


@app.route('/', methods=['GET', 'POST'])
def index():
    print('index route')
    print('is authenticated: {}'.format(current_user.is_authenticated()))
    playlist_url = None
    artists=[]
    playlists=[]
    if current_user.is_authenticated():
        sign_in = False
        user = rdio_oauth_tokens.find_one({'user_key': current_user.get_id()})
        user_icon = user['user_icon']
        user_name = user['user_name']
        try:
            user_playlists = user['previous_playlists']
            for playlist in user_playlists:
                print playlist
        except:
            print('no playlists')
            pass
        print('user name: {}'.format(user_name))
    else:
        sign_in = True
        user_icon = None
        user_name = None
    if request.method == 'POST':
        print('user name: {}'.format(user_name))
        if 'signin' in request.form.keys():
            rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET))
            auth_url = rdio.begin_authentication('http://blametommy.com:5000/')
            oauth_dancer.oauth_token = rdio.token
            return redirect(auth_url)
        if 'artistname' in request.form.keys():
            token = tuple(user['token'])
            rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), token)
            search_artist = request.form['artistname']
            search_result = rdio.call('search',
                                      {'query': search_artist,
                                       'types': 'Artist'})
            search_result = search_result['result']['results']
            artists = []
            for artist in search_result:
                artists.append({
                    'name': artist['name'],
                    'url': artist['shortUrl'],
                    'key': artist['key']})
            '''
            return render_template('index.html',
                                   artists=artists,
                                   sign_in=sign_in,
                                   user_icon=user_icon,
                                   user_name=user_name)
            '''
        if 'create playlist' in request.form.keys():
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
            print(created_playlist)
            playlist_url = created_playlist['result']['url']
            user = rdio_oauth_tokens.find_one({'user_key': current_user.get_id()})
            print(user)
            if 'previous_playlists' not in user.keys():
                print('previous playlists not in user keys')
#                rdio_oauth_tokens.insert({user['previous_playlists'] = []})
            else:
                print('adding playlists to user, need to redo mongodb')
                # should be an insert
                user['previous_playlists'].append([artist, playlist_url])
                print user['previous_playlists']
            print(user)
            return redirect('http://rdio.com{}'.format(playlist_url))
    if request.method == 'GET':
        if current_user.is_authenticated():
            print('GET, user is authenticated')
            token = tuple(user['token'])
            rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), token)
            sign_in = False
        if 'oauth_token' in request.args.keys():
            print('GET, oauth token in request keys')
            rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET),
                        oauth_dancer.oauth_token)
            rdio.complete_authentication(request.args.get('oauth_verifier'))
            oauth_dancer.access_token = rdio.token
            rdio = Rdio((CONSUMER_KEY, CONSUMER_SECRET), rdio.token)
            user = rdio.call("currentUser")['result']
            user_key, user_icon, user_name = user['key'], user['icon'], user['firstName']
            if rdio_oauth_tokens.find_one({'user_key': user_key}) is None:
                print('user not in database')
                print(rdio_oauth_tokens.insert({'user_key': user_key,
                                                'token': rdio.token,
                                                'user_icon': user_icon,
                                                'user_name': user_name}))
            else:
                print('user found in database')
                pass
            session_user = flask_login_user(user_key)
            print('LOGGING IN {}'.format(session_user))
            login_user(session_user)
            session['logged_in'] = True
            sign_in = False
            return redirect('/')
    return render_template('index.html', artists=artists, sign_in=sign_in, user_icon=user_icon,
                           user_name=user_name, playlist_url=playlist_url)



if __name__ == '__main__':
    app.run(host='blametommy.com')
