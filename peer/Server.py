import asyncio
from typing import List
from cli.torrentLogger import logger
from cli.FileIO import FileIO
from peer import Messages as msg
from peer.Client import Client
from peer.RemotePeer import RemotePeer


class Server:
    remotePeersCurr: List[RemotePeer]
    clientTasks: List[RemotePeer]
    fileIO: FileIO
    id: bytes
    updated: bool
    loop: asyncio.AbstractEventLoop

    def __init__(
        self,
        ID: bytes,
        fileIO: FileIO,
        loop: asyncio.AbstractEventLoop,
        clients,
        clientTasks,
    ):
        self.remotePeersCurr = []
        self.fileIO = fileIO
        self.id = ID
        self.loop = loop
        self.clients = clients
        self.clientTasks = clientTasks
        pass

    async def handleConnection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        bytesRecv = await reader.read(68)
        info_hash, peer_info = msg.Handshake.decodeMsg(bytesRecv)
        extraInformation = writer.get_extra_info("peername")
        logger.info(f"Server: Handshake recv from: {extraInformation!r}")

        if self.fileIO.hasTorrent(info_hash):
            hand = msg.Handshake(info_hash, self.id)
            writer.write(hand.encodeMsg())

            remotePeer = RemotePeer(
                extraInformation[0],
                int(extraInformation[1]),
                None,
                self.fileIO.getTorrent(info_hash),
                reader,
                writer,
            )
            remotePeer.initialized = True

            foundClient = False
            for client in self.clients:
                if client.torrent.info_hash == info_hash:
                    client.addServerPeer(remotePeer)
                    foundClient = True
                    break

            if not foundClient:
                client = Client(
                    remotePeer.torrent, [remotePeer], self.fileIO, self.id, None
                )
                self.clients.append(client)
                clientTask = asyncio.create_task(client.start([remotePeer]))
                self.clientTasks.append(clientTask)

            await writer.drain()
        else:
            writer.close()
