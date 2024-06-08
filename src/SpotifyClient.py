import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import qrcode
from flask import Flask, request
from dataclasses import dataclass
import logging
import requests
from PIL import Image
import io


QR_CODE_FILENAME = "spotify_auth_qr.png"
SCOPE = "user-read-currently-playing"

logging.basicConfig(format='[%(levelname)s] %(asctime)s - (%(name)s): %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
load_dotenv()
ALBUM_IMAGE_PATH = os.getenv('COVER_IMG_CACHE_DIR')
ALBUM_LIST = os.getenv('COVER_IMG_CACHE_LIST')


class SpotifyClient:
    downloadedCovers = []
    
    def __init__(self, client_id, client_secret, redirect_uri, scope):
        print("Initializing Spotify client...")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.sp_oauth = SpotifyOAuth(client_id=self.client_id, client_secret=self.client_secret, redirect_uri=self.redirect_uri, scope=self.scope)
        self.token_info = None
        self.get_qr_code()
        self.ensureAlbumImageCacheDir()
        self.loadAlbumImageCache()
        
    def ensureAlbumImageCacheDir(self):
        if not os.path.exists(ALBUM_IMAGE_PATH):
            os.makedirs(ALBUM_IMAGE_PATH)
            
    def loadAlbumImageCache(self):
        if os.path.exists(ALBUM_LIST):
            with open(ALBUM_LIST, 'r') as file:
                self.downloadedCovers = file.read().splitlines()

    def get_auth_url(self):
        auth_url = self.sp_oauth.get_authorize_url()
        return auth_url

    def get_qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        auth_url = self.get_auth_url()
        print(f"Authorization URL: {auth_url}")
        qr.add_data(auth_url)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        # delete the previous QR code if it exists
        if os.path.exists(QR_CODE_FILENAME):
            os.remove(QR_CODE_FILENAME)
        img.save(QR_CODE_FILENAME)

    def get_token(self):
        token_info = self.sp_oauth.get_cached_token()
        if not token_info:
            url = request.url
            code = self.sp_oauth.parse_response_code(url)
            if code:
                token_info = self.sp_oauth.get_access_token(code)
        return token_info['access_token']

    def get_current_track(self):
        token = self.get_token()
        if token:
            sp = spotipy.Spotify(auth=token)
            result = sp.current_user_playing_track()
            return result
        else:
            return None
    
    def fetchCurrentlyPlaying(self, downloadCover=False):
        logging.debug('fetchCurrentlyPlaying')
        currentTrack: dict = self.get_current_track()
        progress: float = currentTrack.get('progress_ms', 0) / currentTrack.get('item', {}).get('duration_ms', 1)
        currPlaying: CurrentlyPlaying = CurrentlyPlaying(
            isPlaying=currentTrack.get('is_playing', False), 
            trackName=currentTrack.get('item', {}).get('name', None),
            artistName=currentTrack.get('item', {}).get('artists', [{}])[0].get('name', None),
            albumName=currentTrack.get('item', {}).get('album', {}).get('name', None),
            albumId=currentTrack.get('item', {}).get('album', {}).get('id', None),
            progress=progress,
            duration=currentTrack.get('item', {}).get('duration_ms', None),
            coverUrl=currentTrack.get('item', {}).get('album', {}).get('images', [{}])[0].get('url', None),
            coverLocalPath=None
        )
        if downloadCover and currPlaying.coverUrl and currPlaying.albumId:
            if currPlaying.albumId not in self.downloadedCovers:
                currPlaying.coverLocalPath = self.downloadCover(currPlaying.albumId, currPlaying.coverUrl)
                self.downloadedCovers.append(currPlaying.albumId)
                with open(ALBUM_LIST, 'a') as file:
                    file.write(currPlaying.albumId + '\n')
            else:
                logging.debug(f"Cover for album {currPlaying.albumId} found in cache.")
                currPlaying.coverLocalPath = f"{ALBUM_IMAGE_PATH}/{currPlaying.albumId}.jpg"
        return currPlaying
    
    def downloadCover(self, id: str, coverUrl: str):
        logging.debug(f"Downloading cover for album {id} from {coverUrl}")
        response = requests.get(coverUrl, stream=True)
        if response.status_code == 200 and response.content:
            img = Image.open(io.BytesIO(response.content))
            img.resize((64, 64))
            localPath = f"{ALBUM_IMAGE_PATH}/{id}.jpg"
            img.save(localPath)
            logging.debug(f"Cover for album {id} saved to {localPath}")
            return localPath
        else:
            logging.error(f"Failed to download cover for album {id} from {coverUrl}")
            return None

@dataclass
class CurrentlyPlaying:
    isPlaying:      bool
    trackName:      str | None
    artistName:     str | None
    albumName:      str | None
    albumId:        str | None
    progress:       int | None
    duration:       int | None
    coverUrl:       str | None
    coverLocalPath: str | None

if __name__ == "__main__":
    load_dotenv()
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')

    app = Flask(__name__)
    spotify_client = SpotifyClient(client_id, client_secret, redirect_uri, scope=SCOPE)
    
    @app.route('/')
    def index():
        access_token = spotify_client.get_token()
        if access_token:
            current_track = spotify_client.get_current_track()
            return current_track
        else:
            spotify_client.get_qr_code()
            return "Please scan the QR code saved as 'spotify_auth_qr.png' and authorize the app."
    
    app.run(port=8080, host="0.0.0.0")
