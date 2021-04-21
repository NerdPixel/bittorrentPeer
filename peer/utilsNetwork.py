import asyncio
from datetime import datetime
import struct
import traceback
from asyncio import IncompleteReadError

from peer import Messages as Messages
from peer.RemotePeer import RemotePeer
from cli.torrentLogger import logger


async def choke(remotePeer: RemotePeer, client, msg: bytes = None):
    remotePeer.status.peerChoking = True
    return 1


async def unchoke(remotePeer: RemotePeer, client, msg: bytes = None):
    remotePeer.status.peerChoking = False
    return 1


async def interested(remotePeer: RemotePeer, client, msg: bytes = None):
    remotePeer.status.peerInterested = True
    remotePeer.status.amChoking = False
    remotePeer.writer.write(Messages.UnchokeMsg().encode())
    await remotePeer.writer.drain()
    return 1


async def notInterested(remotePeer: RemotePeer, client, msg: bytes = None):
    remotePeer.status.peerInterested = False
    remotePeer.status.amChoking = True
    remotePeer.writer.write(Messages.ChokeMsg().encode())
    await remotePeer.writer.drain()
    return 1


async def have(remotePeer: RemotePeer, client, msg: bytes = None):
    if len(msg) != 4:
        # logging.debug("unexpected HaveMsg")
        return -1
    pieceIDx = Messages.HaveMsg.decode(msg)
    remotePeer.availablePieces[pieceIDx] = 1
    remotePeer.calc_possible_pieces(client.requests)
    # logging.debug("HaveMsg von Peer" + str(remotePeer.ip) + "PieceIDx:" + pieceIDx)
    return 1


async def bitfield(remotePeer: RemotePeer, client, msg: bytes = None):
    remotePeer.availablePieces = Messages.BitfieldMsg.decode(msg)[
        : client.torrent.getNumPieces()
    ]
    remotePeer.status.amInterested = True
    remotePeer.calc_possible_pieces(client.requests)
    try:
        remotePeer.writer.write(Messages.InterestedMsg().encode())
        await remotePeer.writer.drain()
        return 1
    except Exception as e:
        logger.error(e)
        return -1


async def request(remotePeer: RemotePeer, client, msg: bytes = None):
    try:
        pieceIdx, begin, length = Messages.RequestMsg.decode(msg)
        piece = remotePeer.torrent.getPiece(pieceIdx)
        # Check if we have Piece
        if not remotePeer.torrent.bitfield[pieceIdx]:
            return 1
        block = piece.read()[begin : min(begin + length, piece.size)]
        client.trackerInfo.bytesSend += length
        remotePeer.writer.write(Messages.PieceMsg(pieceIdx, begin, block).encode())
        await remotePeer.writer.drain()
    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
    return 1


async def piece(remotePeer: RemotePeer, client, msg: bytes = None):
    try:
        pieceIdx, blockIdx, data = Messages.PieceMsg.decode(msg)
        status = remotePeer.torrent.getPiece(pieceIdx).writeBlock(blockIdx, data)
        if status >= 0:
            if status == 1:
                logger.debug("#RemotePeers: " + str(len(client.remotePeersCurr)))
                for peer in client.remotePeersCurr:
                    if not peer.availablePieces[pieceIdx]:
                        try:
                            peer.writer.write(Messages.HaveMsg(pieceIdx).encode())
                            await peer.writer.drain()
                        except BrokenPipeError as E:
                            logger.debug(E)

            if remotePeer.requestQueue:
                reqMsg = remotePeer.requestQueue.pop()
                remotePeer.writer.write(reqMsg.encode())
                await remotePeer.writer.drain()
            else:
                remotePeer.downloading = False
        else:
            logger.error("Fehler in write Piece idx: " + str(pieceIdx))
            return -1
        return 1
    except Exception:
        logger.error("Connection lost! Fehler in receive Piece")
        return -1


async def handleIncomingMsg(remotePeer: RemotePeer, client) -> int:
    # logging.basicConfig(level=logger.error)
    reader = remotePeer.reader
    writer = remotePeer.writer
    msgLenByt = -1
    try:
        await asyncio.sleep(0.1)
        try:
            msgLenByt = await reader.readexactly(4)
        except IncompleteReadError:
            logger.error("Incomplete Read error " + str(remotePeer))
            # logging.debug(traceback.format_exc())
            return 1
        if len(msgLenByt) == 0:
            remotePeer.lastMessageRecv = datetime.now()
            writer.write(Messages.KeepAliveMsg().encode())
            await writer.drain()
            return 1
        remotePeer.lastMessageRecv = datetime.now()
        msgLen = struct.unpack(">i", msgLenByt)[0]
        if msgLen > 0:
            idxByte = await reader.readexactly(1)
            idx = struct.unpack(">B", idxByte)[0]
            await asyncio.sleep(0.1)
            rawMsg = await reader.readexactly(msgLen - 1)
            if idx < 0 or idx > 7:
                logger.error("unexpected MsgId", str(msgLen), str(idx))
                return 1
            handler = {
                0: choke,
                1: unchoke,
                2: interested,
                3: notInterested,
                4: have,
                5: bitfield,
                6: request,
                7: piece,
            }[idx]
            return await handler(remotePeer, client, rawMsg)
    except Exception as e:
        logger.error("Fehler in receive prozess bei " + str(remotePeer.ip))
        logger.error(traceback.format_exc())
        return -1
