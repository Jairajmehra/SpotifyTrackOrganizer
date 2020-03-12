# About SpotifyTrackOrganizer
It is a simple program that organize all the tracks from a master playlist (provided by the user as a name of a playlist) into 3 separate sub-playlist namely Hindi, English and foreign based on the language of the track.

## How it work?
First, I obtain all the playlists a user has then find the specific playlist user wants to sort then extract all songs in that playlist. After having all the tracks of the playlist I use musixmatch's database to determine the language of the song if musixmatch do not have data for a particular track I use a python library called googletrans to detect language based on the title and album name. 
I also included a function which removes duplicates from a playlist.
