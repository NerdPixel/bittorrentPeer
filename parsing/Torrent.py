from typing import List
from bitarray import bitarray

from parsing.BencodingParser import BencodingParser
from parsing.utils import decodeStr, get
from parsing.File import File
from parsing.Piece import PieceList, Piece


class TorrentInfo:
    # mandatory
    piece_length: int
    pieces: PieceList
    name: str  # filename in single file mode, dictionary name in multi file mode
    mode: str  # single_file / multi_file
    files: List[File]

    # optional
    private: int

    def __init__(self, dict, save_path: str, torrent):
        self.piece_length = dict["piece length"]
        self.private = get(dict, "private", None)
        self.name = dict["name"].decode("utf-8")
        self.files = []

        if "files" in dict:
            # Multi file mode
            for f in dict["files"]:
                t = File(save_path, f["path"], get(f, "md5sum", b""), f["length"])
                self.files.append(t)
            self.mode = "multi_file"
        else:
            # single file mode
            self.files.append(
                File(
                    save_path, [dict["name"]], get(dict, "md5sum", b""), dict["length"]
                )
            )
            self.mode = "single_file"

        self.pieces = PieceList(dict["pieces"], self.piece_length, self.files, torrent)


class TorrentFile:
    # Mandatory
    announce: str
    info: TorrentInfo
    info_hash: bytes

    # Optional
    comment: str
    created_by: str
    creation_date: str
    encoding: str
    announce_list: List[str]

    path: str
    save_path: str
    pieceCounter: int
    downloaded: bool

    def __init__(self, path: str, save_path: str, progressBar=None):
        parser = BencodingParser(path)
        dict = parser.parse()

        self.info_hash = parser.info_hash
        self.path = path
        self.save_path = save_path + "/" + self.info_hash.hex() + "/" + "files"

        # Mandatory
        self.announce = dict["announce"].decode("utf-8")
        self.info = TorrentInfo(dict["info"], self.save_path, self)

        # Optional
        self.created_by = get(dict, "created by", b"").decode("utf-8")
        self.creation_date = get(dict, "creation date", None)
        self.comment = get(dict, "comment", b"").decode("utf-8")
        self.encoding = get(dict, "encoding", b"").decode("utf-8")
        self.announce_list = list(
            map(lambda x: list(map(decodeStr, x)), get(dict, "announce-list", []))
        )
        self.bitfield = self.getBitfield()
        self.downloaded = self.bitfield.all()
        self.pieceCounter = len(list(filter(lambda x: x, self.bitfield)))

        if progressBar is not None:
            self.progressBar = progressBar
            progressBar.length = len(self.info.pieces.pieces)
            self.progressBar.update(self.pieceCounter)

    def getPiece(self, idx: int):
        return self.info.pieces.pieces[idx]

    def getNumPieces(self):
        return len(self.info.pieces.pieces)

    def getBitfield(self):
        bitfield = len(self.info.pieces.pieces) * bitarray("0")
        for idx in range(0, len(bitfield)):
            try:
                self.getPiece(idx).read()
                bitfield[idx] = 1
            except Exception:
                continue
        return bitfield
