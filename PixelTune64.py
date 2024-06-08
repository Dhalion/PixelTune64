import logging.config
import schedule
import time
import logging
from dotenv import load_dotenv
from src import SpotifyClient
import os

SCOPE = "user-read-currently-playing"

POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL'))
logging.basicConfig(format='[%(levelname)s] %(asctime)s - (%(name)s): %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')

class PixelTune64:
    spotifyClient: SpotifyClient.SpotifyClient = None
    currentlyPlaying: SpotifyClient.CurrentlyPlaying = None
    
    def __init__(self):
        logging.debug('initPixelTune64')
        schedule.every(POLLING_INTERVAL).seconds.do(self.fetchCurrentlyPlaying)  # ersetzen Sie 5 durch die Anzahl der Sekunden, die Sie warten möchten
        

    def fetchCurrentlyPlaying(self):
        logging.debug('fetchCurrentlyPlaying')
        self.currentlyPlaying = self.spotifyClient.fetchCurrentlyPlaying(downloadCover=True)

    def initClient(self):
        
        logging.debug('initClient')
        load_dotenv()
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')
        self.spotifyClient = SpotifyClient.SpotifyClient(client_id, client_secret, redirect_uri, scope=SCOPE)


if __name__ == '__main__':
    pixelTune = PixelTune64()
    pixelTune.initClient()
    schedule.every(POLLING_INTERVAL).seconds.do(pixelTune.fetchCurrentlyPlaying)  # ersetzen Sie 5 durch die Anzahl der Sekunden, die Sie warten möchten
    
    while True:
        schedule.run_pending()
        time.sleep(1)
    