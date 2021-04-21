import asyncio
import random
import traceback
from typing import List
from datetime import datetime

from cli.FileIO import FileIO
from peer import Messages
from peer.RemotePeer import RemotePeer
from parsing.Torrent import TorrentFile
from bitarray import *
import peer.utilsNetwork as utilsNet
from cli.torrentLogger import logger


class TrackerInfo:
    bytesSend: int

    def __init__(self):
        self.bytesSend = 0


class Client:
    torrent: TorrentFile
    remotePeersPossible: List[RemotePeer]
    remotePeersCurr: List[RemotePeer]
    fileIO: FileIO
    id: bytes
    updated: bool
    availablePieces: bitarray
    peersdownload = False
    requests = dict()
    downloadDict = dict()
    trackerInfo: TrackerInfo

    def __init__(
        self,
        torrent: TorrentFile,
        remotePeersPossible: List[RemotePeer],
        fileIO: FileIO,
        ID: bytes,
        progressBar,
    ):
        self.torrent = torrent
        self.remotePeersPossible = remotePeersPossible
        self.remotePeersCurr = []
        self.fileIO = fileIO
        self.id = ID
        self.updated = True
        self.availablePieces = self.torrent.bitfield
        self.createRequestQueue()
        self.progressBar = progressBar
        self.trackerInfo = TrackerInfo()

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.torrent.info_hash == other.torrent.info_hash
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    async def handleHandshake(self, reader, extraInformation, peer) -> bool:
        for tries in range(5):
            answer = await reader.read(Messages.Handshake.LENGTH)
            if answer:
                break
            await asyncio.sleep(0.2)
        # print(answer)
        if not answer:
            # print('No handshake answer!')
            return False
        res = Messages.Handshake.decodeMsg(answer)
        if res[0] != self.torrent.info_hash:
            # print('Info Hash does not match!')
            return False
        # print('Client: handshake successful with ' + str(extraInformation))
        return True

    async def sendHandshake(self, writer):
        hadshakeMsg = Messages.Handshake(self.torrent.info_hash, self.id)
        writer.write(hadshakeMsg.encodeMsg())
        await writer.drain()
        extraInformation = writer.get_extra_info("peername")
        # print(f"Client: Handshake sent to: {extraInformation!r}")

    def filterList(self, peer) -> bool:
        return not peer in self.remotePeersCurr

    def addServerPeer(self, remotePeer: RemotePeer):
        self.remotePeersPossible.append(remotePeer)
        self.updated = True

    def updatePeers(self, updatedRemotePeersPossible: List[RemotePeer]):
        logger.error("updating peers...")
        self.updated = True
        newPeers = list(filter(self.filterList, updatedRemotePeersPossible))
        cutoff = max(len(self.remotePeersPossible), 50)
        self.remotePeersPossible += newPeers
        self.remotePeersPossible = self.remotePeersPossible[:cutoff]

    async def downloadPieces(self, remotePeer):
        self.progressBar.label = str(len(self.remotePeersCurr)) + " Peers"
        if (
            not remotePeer.status.peerChoking
            and remotePeer.status.amInterested
            and remotePeer.requestQueue
        ):
            remotePeer.downloading = True
            if remotePeer.firstDownload:
                remotePeer.firstDownload = False
                for i in range(0, 7):
                    remotePeer.writer.write(remotePeer.requestQueue.pop().encode())
                    await remotePeer.writer.drain()
            else:
                remotePeer.writer.write(remotePeer.requestQueue.pop().encode())
                await remotePeer.writer.drain()

    async def askPeers(self, peer: RemotePeer):
        try:
            fut = asyncio.open_connection(peer.ip, peer.port)
            reader, writer = await asyncio.wait_for(fut, timeout=2)
            await self.sendHandshake(writer)
            extraInformation = writer.get_extra_info("peername")
            succeed = await self.handleHandshake(reader, extraInformation, peer)
            if succeed:
                peer.lastMessageRecv = datetime.now()
                peer.writer = writer
                peer.reader = reader
                peer.torrent = self.torrent
                # handshake successful -> set flag and send interested message
                self.remotePeersCurr.append(peer)
                return peer
        except asyncio.TimeoutError:
            logger.error("Timeout, skipping" + str(peer.ip))
        except Exception as e:
            logger.error(e)

    async def coro(self, peer: RemotePeer):
        # logging.basicConfig(level=logging.DEBUG)
        if not peer.initialized:
            remotePeer = await self.askPeers(peer)
        else:
            remotePeer = peer

        if not isinstance(remotePeer, RemotePeer):
            return

        b = Messages.BitfieldMsg(self.torrent.bitfield)
        remotePeer.writer.write(b.encode())
        await remotePeer.writer.drain()

        remotePeer.initialized = True
        timeStamp = datetime.now()
        while True:
            if self.torrent.downloaded and remotePeer.availablePieces.all():
                self.removeOfflinePeer(remotePeer)
                return
            try:
                if (datetime.now() - timeStamp).total_seconds() >= 120:
                    remotePeer.writer.write(Messages.KeepAliveMsg.encode())
                    await remotePeer.writer.drain()
                    timeStamp = datetime.now()
            except Exception:
                logger.debug("Connection lost!")
                self.removeOfflinePeer(remotePeer)
            status = await utilsNet.handleIncomingMsg(remotePeer, self)

            if status == -1 or (
                self.torrent.downloaded
                and (datetime.now() - remotePeer.lastMessageRecv).total_seconds() >= 30
            ):
                self.removeOfflinePeer(remotePeer)
                return

            if (
                not self.torrent.downloaded
                and not remotePeer.downloading
                and remotePeer.availablePieces.any()
            ):
                try:
                    requestPieceList = self.getRequestPieceList(remotePeer)
                    if requestPieceList == 1:
                        continue

                    if requestPieceList == None:
                        print("Finished with peer")
                        return

                    for blockMsg in requestPieceList:
                        remotePeer.requestQueue.append(blockMsg)
                    await asyncio.sleep(0.1)
                    await self.downloadPieces(remotePeer)
                except Exception as e:
                    logger.error(e)
                    logger.error("Fehler in coro")
                    logger.error(traceback.format_exc())

    async def start(self, peerList: [RemotePeer] = []):
        tasks = []
        tasks.append(asyncio.create_task(self.dummy_coro()))

        while tasks:
            finished, unfinished = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            tasks = list(unfinished)
            if self.updated:
                for new_peer in self.remotePeersPossible:
                    if self.filterList(new_peer):
                        task = asyncio.create_task(self.coro(new_peer))
                        tasks.append(task)
                self.updated = False
            tasks.append(asyncio.create_task(self.dummy_coro()))
        # await asyncio.gather(*tasks)
        logger.debug("Client is ready")

    async def dummy_coro(self):
        await asyncio.sleep(0.1)
        # while not self.updated:
        #     await asyncio.sleep(0.1)

    def createRequestQueue(self):
        for pieceIDx, have in enumerate(self.availablePieces):
            if have:
                continue
            pieceBlocks = []
            for block in self.torrent.info.pieces.pieces[pieceIDx].blocks:
                pieceBlocks.append(
                    Messages.RequestMsg(pieceIDx, block.start, block.size)
                )
            self.requests[pieceIDx] = pieceBlocks

    def removeOfflinePeer(self, peer):
        logger.debug("Lost Peer: " + str(peer.ip) + ":" + str(peer.port))
        self.requests[peer.requestPieceIdx] = peer.requestPiece
        if peer in self.remotePeersPossible:
            self.remotePeersPossible.remove(peer)

        if peer in self.remotePeersCurr:
            self.remotePeersCurr.remove(peer)

    def getRequestPieceList(self, remotePeer):
        if len(self.requests) == 0:
            if self.availablePieces.all():
                return None
            else:
                self.createRequestQueue()
                remotePeer.calc_possible_pieces(self.requests)
                logger.debug("created Request Queue!")

        if not remotePeer.possiblePieces:
            is_empty = remotePeer.calc_possible_pieces(self.requests)
            if is_empty:
                # self.removeOfflinePeer(remotePeer)
                return 1

        while remotePeer.possiblePieces:
            requestPieceIdx = random.choice(remotePeer.possiblePieces)
            remotePeer.possiblePieces.remove(requestPieceIdx)
            if requestPieceIdx in self.requests:
                break

        try:
            requestPieceList = self.requests.pop(requestPieceIdx)
        except KeyError:
            return 1

        remotePeer.requestPiece = requestPieceList
        remotePeer.requestPieceIdx = requestPieceIdx

        return requestPieceList
