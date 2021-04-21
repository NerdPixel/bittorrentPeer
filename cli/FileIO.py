import os
import shutil
from parsing.Torrent import TorrentFile

"""
save_folder
    -> torrent1
        -> files
        -> torrent.torrent
    -> torrent2
        -> files
        -> torrent.torrent
"""


class FileIO:
    # pfad in dem gespeichert werden soll
    save_path: str
    # liste an torrents die wir haben
    torrent_list = []

    def __init__(self, save_path: str):
        self.save_path = save_path

        # liste initial füllen
        # save path ordner ggfs erstellen
        if os.path.isdir(save_path):
            self.torrent_list = os.listdir(save_path)
        else:
            # os.chdir('./')
            os.mkdir(save_path)

    # ist der infohash in der liste
    def hasTorrent(self, info_hash: bytes) -> bool:
        for i in self.torrent_list:
            if i == info_hash.hex():
                return True
        return False

    # torrent datei einlesen von festplatte
    def getTorrent(self, info_hash: bytes) -> TorrentFile:
        path = (
            self.save_path + "/" + info_hash.hex() + "/" + info_hash.hex() + ".torrent"
        )
        # sind die paths richtig?
        return TorrentFile(path, self.save_path)

    # torrent datei hinzufügen
    def addTorrent(self, torrent: TorrentFile):
        if self.hasTorrent(torrent.info_hash):
            return

        hex = torrent.info_hash.hex()
        folderPath = f"{self.save_path}/{hex}"
        # Ordnerstruktur für torrent erstellen

        if not os.path.exists(folderPath):
            os.makedirs(folderPath)

        # torrent in ordner kopieren
        shutil.copy(torrent.path, f"{folderPath}/{hex}.torrent")

        # hash zu der liste hinzufügen
        self.torrent_list.append(hex)
