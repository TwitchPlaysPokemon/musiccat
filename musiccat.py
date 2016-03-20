# TPPBR MusicCat Song Library v2.3
# Dependencies: pyyaml, python-Levenshtein, pypiwin32
# Please install all with pip3

# (note: if installing python-Levenshtein complains about vcvarsall.bat,
#  see http://stackoverflow.com/a/33163704)

from __future__ import print_function
try:
    from builtins import input
except: # Temporary hack until the builtins future module is properly installed
    input = raw_input

# pip3 dependencies
import Levenshtein
import yaml

# standard modules
import os
import subprocess
import logging
from bson import CodecOptions, SON

import winamp

class NoMatchError(ValueError):
    """Raised when a song id fails to match a song with any confidence"""
    def __init__(self, songid):
        super(NoMatchError, self).__init__("Song ID {} not found.".format(songid))
        self.songid = songid

class MusicCat(object):

    def __init__(self, library_path):
        self.winamp = winamp.Winamp()
        self.log = logging.getLogger("musicCat")
	self.songs = {}

	self.refresh_song_list()

    def refresh_song_list(self, root_path):
        """ Clears songlist and loads all metadata.yaml files under the root directory"""
        self.songs = {}
        for root, dirs, files in os.walk(root_path):
            for filename in files:
                if filename.endswith(".yaml"):
                    metafilename = os.path.join(root, filename)
                    try:
                        self.import_metadata(metafilename)
                    except Exception as e:
                        print("Exception while loading file {}: {}".format(metafilename, e))
    """
    Metadata.yaml format:

     - id: gameid
       title:
       series:
       year:
       platform:
       path: # No longer used
       songs:
        - id:
          title:
          path:
          type: type
          types: [type, type] #one or the other, depending on multiple
    """

    def import_metadata(self, metafilename):
        """Import metadata given a metadata filename. Assumed to be one game per metadata file."""
        with open(metafilename) as metafile:
            gamedata = yaml.load(metafile)
        path = os.path.dirname(metafilename)
	newsongs = {}

        gameid = gamedata["id"]
        system = gamedata["platform"]
        songs = gamedata.pop("songs")
        for song in songs:
            if song["id"] in self.songs:
                self.log.warn("Songid {} exists twice, once in {} and once in {}! Ignoring duplicate. ".format(song["id"], self.songs[song["id"]]["game"]["id"], gameid))
            if song["id"] in newsongs:
                self.log.warn("Songid {} exists twice in the same game, {}. Ignoring duplicate.".format(song["id"], gameid))
            song["fullpath"] = os.path.join(path, song["path"])
            song["game"] = gamedata
            if "type" in song: # Convert single type to a stored list
                song["types"] = [song.pop("type")]
            newsongs[song["id"]] = song

        # All data successfully imported; apply to existing metadata
        self.songs.update(newsongs)

    def play_file(self, songfile):
        """ Runs Winamp to play given song file. 
            Though this may appear to, using subprocess.Popen does not leak memory because winamp makes the processes all exit."""
        self.winamp.stop()
        self.winamp.clearPlaylist()
        p = subprocess.Popen('"{0}" "{1}"'.format(self.winamp_path, songfile))

    def get_song_info(self, songid):
        """Return named tuples for a given (valid) songid.
	Will raise a ValueError if the songid does not exist.
        """
        if songid.find("-") > 0: # Dash separates game and song id
            gameid, songid = songid.split("-")
        return self.songs[songid]

    def search(self,songid):
        """Search through all songs in self.songs; return any IDs close to what is typed out."""
        #Try exact match
        song = self.songs.get(songid, None)

        #If that didn't work, get all songs that seem close enough
        if song is None:
            best_ratio = 0
            best_match = None
            for s in self.songs:
                ratio = Levenshtein.ratio(songid, s)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = s
            if best_ratio < self.minimum_autocorrect_ratio: # No close enough match, tell user closest match
                raise BadMatchError(songid, best_match)
            elif best_ratio < self.minimum_match_ratio: # No match close enough to be reliable
                raise NoMatchError(songid)
            else: # close enough to autocorrect for them.
                song = self.songs[best_match]
        return song

    def play_next_song(self, songid):
        """ Play a song. May raise a ValueError if the songid doesn't exist."""
        nextsong = self.songs[songid]
        self.current_song = nextsong
        self.play_file(nextsong["fullpath"])
        self.log.info("Now playing {}".format(nextsong))

    def set_winamp_volume(self, volume):
        """Update winamp's volume. Volume goes from 0 to 1"""
        if (volume < 0) or (volume > 1):
            raise ValueError("Volume must be between 0 and 1")
        #winamp expects a volume from 0 to 255
        self.winamp.setVolume(volume*255)

    def pause_winamp(self):
        pass

    def unpause_winamp(self):
        pass

    def print_total_amt_songs(self, category=None):
        """Print the total number of songs, either for all songs or for a specific category if one is given."""
        pass

if __name__ == "__main__":
    pass
