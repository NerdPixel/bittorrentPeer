import asyncio
import logging
import click
from typing import List

from cli.FileIO import FileIO
from parsing.Torrent import TorrentFile
from peer.Client import Client
from peer.Server import Server
from tracker.Tracker import TrackerProtokoll
from pathlib import Path
from cli.torrentLogger import logger


class CLI:
    clients: List[Client]
    clientTasks: List[asyncio.Task]
    server: Server
    fileIO: FileIO
    loop: asyncio.AbstractEventLoop
    serverPortIncoming: int
    serverPortOutgoing: int
    torrentFile: str
    savePath: str
    tracker: TrackerProtokoll
    torrent: TorrentFile
    logger: logging

    def __init__(self, torrent, out, incoming, outgoing):
        self.serverPort = int(incoming)
        self.serverPortRemote = int(outgoing)
        self.savePath = str(out)
        Path("../" + str(out) + "/").mkdir(parents=True, exist_ok=True)
        self.torrentFile = str(torrent)
        self.fileIO = FileIO(self.savePath)
        self.ID = bytes(20)
        self.clients = []
        self.clientTasks = []
        asyncio.run(self.setupLoop())

    def startServer(self):
        self.server = Server(
            self.ID, self.fileIO, self.loop, self.clients, self.clientTasks
        )
        return asyncio.start_server(
            self.server.handleConnection, "localhost", self.serverPort
        )

    async def add_client_tasks(self):
        tasks = list.copy(self.clientTasks)
        tasks.append(asyncio.create_task(self.dummy_coro()))
        self.clientTasks = []

        while tasks:
            finished, unfinished = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            tasks = list(unfinished)

            if self.clientTasks:
                tasks += self.clientTasks
                self.clientTasks = []
            tasks.append(asyncio.create_task(self.dummy_coro()))

    async def dummy_coro(self):
        await asyncio.sleep(0.1)

    def parse(self, progressBar) -> TorrentFile:
        return TorrentFile(self.torrentFile, self.savePath, progressBar)

    async def setupLoop(self):
        label = ""

        with click.progressbar(
            label=label, length=100, width=70, show_eta=True
        ) as progressBar:
            self.loop = asyncio.get_running_loop()
            self.torrent = self.parse(progressBar)
            self.fileIO.addTorrent(self.torrent)

            downloadTask = self.startDownload(self.torrent, progressBar)
            serverTask = await self.startServer()
            addClientTask = self.add_client_tasks()

            await asyncio.gather(
                addClientTask, serverTask.serve_forever(), downloadTask
            )

    async def getPeersIntervall(
        self, tracker: TrackerProtokoll, client: Client, torrent: TorrentFile
    ):
        while True:
            if torrent.downloaded:
                return
            await asyncio.sleep(tracker.interval)

            bytesTotal = len(torrent.info.pieces.pieces) * torrent.info.piece_length
            bytesDown = torrent.pieceCounter * torrent.info.piece_length

            peers = tracker.get_peers(
                client.trackerInfo.bytesSend, bytesDown, bytesTotal - bytesDown
            )
            try:
                client.updatePeers(peers)
            except Exception as e:
                logger.error(e)

            await asyncio.sleep(tracker.interval)
        pass

    def startDownload(self, torrent: TorrentFile, progressBar):
        self.tracker = TrackerProtokoll(torrent)
        remotePeers = self.tracker.get_peers(
            0, 0, len(torrent.info.pieces.pieces) * torrent.info.piece_length
        )
        # remotePeers = []
        # if self.serverPortRemote == 3000:
        #     remotePeers.append(
        #         RemotePeer("localhost", self.serverPortRemote, torrent=self.torrent)
        #     )

        client = Client(torrent, remotePeers, self.fileIO, self.ID, progressBar)
        self.clients.append(client)
        clientTask = asyncio.create_task(client.start(remotePeers))
        intervallTask = asyncio.create_task(
            self.getPeersIntervall(self.tracker, client, torrent)
        )
        return asyncio.gather(intervallTask, clientTask)


@click.command()
@click.option("--incoming", default=3002, help="Server port for incoming connections")
@click.option("--outgoing", default=3003, help="Server port for outgoing connections")
@click.option("--torrent", help="Path to torrent file", type=click.Path(exists=True))
@click.option("--out", help="Path to saving directory", type=click.Path(exists=True))
def init(out, torrent, incoming, outgoing):
    cli = CLI(torrent, out, incoming, outgoing)


if __name__ == "__main__":
    init()
