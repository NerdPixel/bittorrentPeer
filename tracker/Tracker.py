import secrets
import requests
import ipaddress
from peer.RemotePeer import RemotePeer
from parsing.BencodingParser import BencodingParser
from cli.torrentLogger import logger


class TrackerProtokoll:
    def __init__(self, torrent):
        self.torrent = torrent
        self.info_hash = torrent.info_hash
        self.url = torrent.announce
        self.peer_id = bytes.fromhex(secrets.token_hex(20))
        self.interval = -1

    def get_peers(self, uploaded, downloaded, left):
        self.interval = 30

        if left > 0:
            event = "started"
        else:
            event = "completed"

        params = {
            "info_hash": self.info_hash,
            "peer_id": self.peer_id,
            "port": "5000",
            "uploaded": uploaded,
            "downloaded": downloaded,
            "left": left,
            "compact": "1",
            "no_peer_id": "0",
            "event": event,
        }
        page = requests.get(self.url, params=params)
        logger.error(params["event"])

        parser = BencodingParser(text=page.content)
        res = parser.parse()

        if res is None:
            return []

        if "failure reason" in res:
            return res["failure reason"]

        # self.interval = res['interval']
        # logging.debug("GOT PEERS! Interval: " + str(res['interval']))
        peers = []

        if isinstance(res["peers"], list):
            for peer in res["peers"]:
                peers.append(
                    RemotePeer(
                        peer["ip"].decode("UTF-8"),
                        int(peer["port"]),
                        torrent=self.torrent,
                    )
                )
        else:
            peer_bytes = bytearray(res["peers"])

            for i in range(0, len(peer_bytes), 6):
                peers.append(
                    RemotePeer(
                        str(ipaddress.IPv4Address(bytes(peer_bytes[i : i + 4]))),
                        int.from_bytes(
                            bytes(peer_bytes[i + 4 : i + 6]), byteorder="big"
                        ),
                        torrent=self.torrent,
                    )
                )
        return peers
