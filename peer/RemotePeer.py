from asyncio import StreamReader, StreamWriter
from bitarray import bitarray
from parsing.Torrent import TorrentFile


class RemotePeerStatus:
    def __init__(self):
        # download
        self.amInterested = False
        self.peerChoking = True
        # seed
        self.peerInterested = False
        self.amChoking = True


class RemotePeer:
    ip: str
    port: int
    id: bytes
    reader: StreamReader
    writer: StreamWriter
    availablePieces: []
    torrent: TorrentFile
    requestQueue: []
    requestWindow: int
    firstDownload: bool
    possiblePieces: []

    def __init__(
        self,
        ip: str,
        port: int,
        id: bytes = None,
        torrent: TorrentFile = None,
        reader: StreamReader = None,
        writer: StreamWriter = None,
    ):
        self.ip = ip
        self.port = port
        self.id = id
        self.reader = reader
        self.writer = writer
        self.status = RemotePeerStatus()
        self.availablePieces = len(torrent.info.pieces.pieces) * bitarray("0")
        self.torrent = torrent
        self.requestQueue = []
        self.requestWindow = 1
        self.downloading = False
        self.firstDownload = True
        self.requestPiece = None
        self.requestPieceIdx = None
        self.lastMessageRecv = None
        self.initialized = False
        self.possiblePieces = []

    def __str__(self):
        return str(self.ip + ":" + str(self.port))

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.ip == other.ip
            and self.port == other.port
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__str__())

    def calc_possible_pieces(self, requests):
        self.possiblePieces = []
        for pieceIdx in requests:
            if self.availablePieces[pieceIdx]:
                self.possiblePieces.append(pieceIdx)

        return len(self.possiblePieces) == 0
