import requests
import MusixMatchAPi as mm
from googletrans import Translator
import spotipy

# List of all regional languages in India, we want all of them to be identified as Hindi
HindiLanguages = ['bn', 'gu', 'kn', 'mg', 'ms', 'ml', 'mr', 'pa', 'ta', 'te', 'ur']

class Spotify:
    def __init__(self, user_name, playlist_name, client_id, secret_key, redirect_url): # Scope can be filtered even further.
        scope = scope = """user-library-read,  playlist-read-collaborative,  
             user-read-private, playlist-modify-public, user-library-modify, 
            playlist-read-private, playlist-modify-private"""
        try:
            token = spotipy.util.prompt_for_user_token(user_name, scope, client_id=client_id, client_secret=secret_key,
                                                       redirect_uri=redirect_url)
            self.sp = spotipy.Spotify(auth=token)
        except Exception:
            print(Exception)
        self.username = user_name
        self.master_playlist_name = playlist_name # Name of the playlist to arrange into sub playlist namely English, Hindi and Foreign
        self.master_playlist_id = None
        self.translator = Translator() # This object will be used to detect language of a track based on title and album name
        self.tracks_dict = {}
        self.hindi_playlist_id = None
        self.english_playlist_id = None
        self.foreign_playlist_id = None
        self.songs_to_skip = [] #

        self.songs_to_addback = [] # If any songs are in Playlist Hindi, English or Foreign and not in the master PlayList then this list will be used to add them to the Master Playlist
        self.songs_to_arrange = [] # List of the songs that are in the master playlist provided by the user but not in the sub playlists, So they need to be put into the right sub playlist
        self.LIMIT = 100 # 100 is the maximum limit supported by spotify APi

    def run(self):
        self.get_user_playlists()

    def get_user_playlists(self):
        playlist_dict = self.sp.current_user_playlists()
        for x in range(len(playlist_dict['items'])):
            if (playlist_dict['items'][x]['name'] == self.master_playlist_name):
                self.master_playlist_id = playlist_dict['items'][x]['id']

            elif (playlist_dict['items'][x]['name'] == 'Hindi'):
                self.hindi_playlist_id = playlist_dict['items'][x]['id']

            elif (playlist_dict['items'][x]['name'] == "English"):
                self.english_playlist_id = playlist_dict['items'][x]['id']

            elif (playlist_dict['items'][x]['name'] == "Foreign"):
                self.foreign_playlist_id = playlist_dict['items'][x]['id']

        self.get_user_tracks()

    def get_user_tracks(self):
        # Check if Playlist exits otherwise create new
        if (self.hindi_playlist_id is None):
            playlist = self.sp.user_playlist_create(self.username, "Hindi")
            self.hindi_playlist_id = playlist['id']
        else:
            self.songs_to_skip += self.fetch_all_songs(self.hindi_playlist_id)

        if (self.foreign_playlist_id is None):
            playlist = self.sp.user_playlist_create(self.username, "Foreign")
            self.foreign_playlist_id = playlist['id']
        else:
            self.songs_to_skip += self.fetch_all_songs(self.foreign_playlist_id)

        if (self.english_playlist_id is None):
            playlist = self.sp.user_playlist_create(self.username, "English")
            self.english_playlist_id = playlist['id']
        else:
            self.songs_to_skip += (self.fetch_all_songs(self.english_playlist_id))


        self.songs_to_arrange += (self.fetch_all_songs(self.master_playlist_id)) # Getting all songs from the user provided master playlist

        self.songs_to_addback = list(set(self.songs_to_skip) - set(self.songs_to_arrange))
        self.songs_to_arrange = list(set(self.songs_to_arrange) - set(self.songs_to_skip))

        self.get_track_data()

    def get_track_data(self):
        # Getting each track data from spotify APi
        for x in range(len(self.songs_to_arrange)):
            track = self.sp.track(self.songs_to_arrange[x])
            self.tracks_dict.update({track['id']: {"Title": track['name'], "Album": track['album']['name'],
                                                 "Artist": track['artists'][0]['name']}})
        # Getting Each track Data from MusixMatch APi
        for x in range(len(self.songs_to_arrange)):
            api_call = mm.base_url + mm.track_search + mm.format_url + mm.artist_search_parameter + \
                       self.tracks_dict[self.songs_to_arrange[x]]['Artist'] + mm.track_search_parameter + \
                       self.tracks_dict[self.songs_to_arrange[x]]['Title'] + mm.api_key
            request = requests.get(api_call)
            data = request.json()

            if (len(data['message']['body']['track_list']) > 0):
                self.tracks_dict[self.songs_to_arrange[x]].update(
                    {'MusixMathID': data['message']['body']['track_list'][0]['track']['track_id']}) # updating MusixMatch track ID
                api_call = mm.base_url + mm.snippet_getter + mm.format_url + mm.track_id_parameter + str(
                    data['message']['body']['track_list'][0]['track']['track_id']) + mm.api_key
                request = requests.get(api_call) # Making another APi call with the track ID optained above
                data2 = request.json()
                if (data2['message']['header']['status_code'] == 200):
                    self.tracks_dict[self.songs_to_arrange[x]].update(
                        {'Lang': data2['message']['body']['snippet']['snippet_language']}) # updating track with lang key and value
                else:
                    self.tracks_dict[self.songs_to_arrange[x]].update({'Lang': None})
            else:
                self.tracks_dict[self.songs_to_arrange[x]].update({'MusixMatchID': None})
                self.tracks_dict[self.songs_to_arrange[x]].update({'Lang': None})

        self.detect_track_language()

    def detect_track_language(self):
        for x in range(len(self.songs_to_arrange)):
            if (self.tracks_dict[self.songs_to_arrange[x]]['Lang'] is None):
                lang = self.translator.detect(
                    self.tracks_dict[self.songs_to_arrange[x]]['Title'] + " " + self.tracks_dict[self.songs_to_arrange[x]]['Album']) # Using track title and album name to detect track language
                if (lang.lang in HindiLanguages):
                    self.tracks_dict[self.songs_to_arrange[x]]['Lang'] = 'hi'
                else:
                    self.tracks_dict[self.songs_to_arrange[x]]['Lang'] = lang.lang

            elif (self.tracks_dict[self.songs_to_arrange[x]]['Lang'] in HindiLanguages):
                self.tracks_dict[self.songs_to_arrange[x]]['Lang'] = 'hi'
            else:
                continue

        self.upload_to_spotify()

    def upload_to_spotify(self):
        hindi = []
        english = []
        foreign = []

        for x in range(len(self.songs_to_arrange)):
            if (self.tracks_dict[self.songs_to_arrange[x]]['Lang'] == "hi"):
                hindi.append(self.songs_to_arrange[x])
            elif (self.tracks_dict[self.songs_to_arrange[x]]['Lang'] == "en"):
                english.append(self.songs_to_arrange[x])
            else:
                foreign.append(self.songs_to_arrange[x])

        if (english):
            self.sp.user_playlist_add_tracks(self.username, self.english_playlist_id, english)
        if (hindi):
            self.sp.user_playlist_add_tracks(self.username, self.hindi_playlist_id, hindi)
        if (foreign):
            self.sp.user_playlist_add_tracks(self.username, self.foreign_playlist_id, foreign)

        self.add_songs_to_master_playlist()
        print("Completed")
        print(str(len(self.songs_to_arrange)) + " " + 'Songs arranged')

    def add_songs_to_master_playlist(self):
        print(str(len(self.songs_to_addback)) + " " + "songs added to " + self.master_playlist_name)
        if (self.songs_to_addback):
            self.sp.user_playlist_add_tracks(self.username, self.master_playlist_id, self.songs_to_addback)

    def fetch_all_songs(self, playlist_id):
        all_tracks_id = []
        songs = self.sp.playlist_tracks(playlist_id, limit=self.LIMIT, offset=0)
        while True:
            for i in range(len(songs['items'])):
                all_tracks_id.append(songs['items'][i]['track']['id'])
            if ((len(songs['items']) >= self.LIMIT)):
                songs = self.sp.playlist_tracks(playlist_id, limit=self.LIMIT,offset=len(songs['items']))
            else:
                return all_tracks_id



    def remove_duplicate(self, playlist_name): # cannot delete more than 100 duplicates (To be fixed)
        playlist_dict = self.sp.current_user_playlists()
        all_tracks_id = []
        duplicate_tracks = []
        id = None
        for x in range(len(playlist_dict['items'])):  # to be optimized, It searches for the playlist name provided by the user, if a playlist exist with that name then extract its id
            if (playlist_dict['items'][x]['name'].lower() == playlist_name.lower()):
                id = playlist_dict['items'][x]['id']
                all_tracks_id = self.fetch_all_songs(id)
            else:
                continue
        if(id!=None):
            if(all_tracks_id):
                for x in range(len(all_tracks_id)):
                    if(all_tracks_id.count(all_tracks_id[x]) > 1):
                        duplicate_tracks.append(all_tracks_id[x])
                    else:
                        continue
            if(duplicate_tracks):
                self.sp.user_playlist_remove_all_occurrences_of_tracks(self.username, id, duplicate_tracks) #To be updated to complete in 1 API call
                add_songs = list(dict.fromkeys(duplicate_tracks))
                self.sp.user_playlist_add_tracks(self.username,id, add_songs)
            print(str(len(duplicate_tracks)) + " " + "Duplicates removed")
        else:
            print("no playlist found with the provided name")




# parameters username, playlistname, clientid, secretkey, redirecturl

s = Spotify( user_name=, playlist_name=,  client_id=,secret_key=, redirect_url='https://www.google.com')
s.run()
s.remove_duplicate(playlist_name='All songs') # playlist name from which to delete duplicates.