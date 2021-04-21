import hashlib
from cli.torrentLogger import logger
import os
from bitarray import bitarray
from peer.constants import BLOCK_SIZE
from typing import List

from parsing.File import File


class Block:
    start: int
    size: int

    def __init__(self, start: int, size: int):
        self.start = start
        self.size = size


class PieceCache:
    blockSize: int
    hasBlock: bitarray

    def __init__(self, piece):
        self.reset(piece)

    def writeBlock(self, blockIdx: int, block: bytes) -> bool:
        start = blockIdx
        self.rawBytes[start : start + len(block)] = block
        self.hasBlock[int(blockIdx / BLOCK_SIZE)] = True
        return self.hasBlock.all()

    def reset(self, piece):
        self.rawBytes = bytearray(piece.size)
        self.hasBlock = bitarray(len(piece.blocks))
        self.hasBlock.setall(False)


class PieceFile:
    file: File
    start: int
    end: int
    size: int

    def __init__(self, file: File, start: int, size: int):
        self.file = file
        self.start = start
        self.size = size
        self.end = start + size


class Piece:
    hash: bytes
    size: int
    blocks: List[Block]
    files: List[PieceFile]
    cache: PieceCache
    downloaded: bool
    idx: int

    def __init__(self, hash: bytes, idx: int, torrent):
        self.hash = hash
        self.files = []
        self.blocks = []
        self.size = -1
        self.torrent = torrent
        self.downloaded = False
        self.idx = idx

    def verify(self, piece: bytes) -> bool:
        hash_new = hashlib.sha1(piece).digest()

        return hash_new == self.hash

    def read(self) -> bytes:
        piece = b""
        for file in self.files:
            p = file.file.getFilepath()
            if not os.path.exists(p):
                raise Exception("Piece not found")

            with open(file.file.getFilepath(), "rb") as f:
                f.seek(file.start)
                piece += f.read(file.size)

        if self.verify(piece):
            return piece
        else:
            raise Exception("Piece not found")

    def write(self, bytes):
        pieceAcc = 0
        if self.verify(bytes):
            for file in self.files:
                with open(
                    file.file.getFilepath(),
                    "r+b" if os.path.exists(file.file.getFilepath()) else "wb",
                ) as f:
                    f.seek(file.start)
                    f.write(bytes[pieceAcc : pieceAcc + file.size])
                    pieceAcc += file.size
            return True
        else:
            return False

    def calc_blocks(self):
        for blockStart in range(0, self.size, BLOCK_SIZE):
            size = min(BLOCK_SIZE, self.size - blockStart)
            self.blocks.append(Block(blockStart, size))
        self.cache = PieceCache(self)

    def writeBlock(self, blockIdx: int, block: bytes):
        if self.torrent.bitfield[self.idx]:
            logger.error("piece exists already")
            return 1

        hasAllBlocks = self.cache.writeBlock(blockIdx, block)
        if hasAllBlocks:
            if self.write(bytes(self.cache.rawBytes)):
                self.torrent.bitfield[self.idx] = 1
                self.torrent.downloaded = self.torrent.bitfield.all()
                self.torrent.pieceCounter += 1

                self.torrent.progressBar.update(1)
                lenPieces = len(self.torrent.info.pieces.pieces)
                logger.info(
                    f"Downloaded: {self.torrent.pieceCounter} / {lenPieces}, {round(self.torrent.pieceCounter / lenPieces * 100, 2)}%"
                )

                self.cache.reset(self)
                return 1
            else:
                return -1
        else:
            return 0

    def readBlock(self, blockIdx: int) -> bytes:
        piece = self.read()

        start = blockIdx * BLOCK_SIZE
        return piece[start : min(start + BLOCK_SIZE, len(piece))]


class PieceList:
    pieces: List[Piece]

    def __init__(self, pieces: bytes, pieceSize: int, files: List[File], torrent):
        self.pieces = []

        hashSize = 20
        curFileIdx = 0
        accFileSize = 0
        for idx, start in enumerate(range(0, len(pieces), hashSize)):
            piece = Piece(pieces[start : start + hashSize], idx, torrent)

            accPieceSize = 0
            while accPieceSize < pieceSize:
                if curFileIdx == len(files):
                    break

                file = files[curFileIdx]
                fileStartPosition = idx * pieceSize - accFileSize + accPieceSize
                fileSize = pieceSize - accPieceSize
                fileEndPosition = fileStartPosition + fileSize

                if file.length <= fileEndPosition:
                    fileSize = file.length - fileStartPosition
                    curFileIdx += 1
                    accFileSize += file.length

                piece.files.append(PieceFile(file, fileStartPosition, fileSize))
                accPieceSize += fileSize

            piece.size = accPieceSize
            piece.calc_blocks()
            self.pieces.append(piece)
