import struct
from bitarray import bitarray


class Handshake:
    LENGTH = 68
    FORMAT = ">B19s8x20s20s"

    def __init__(self, info_hash, peer_id):
        self.info_hash = info_hash
        self.peer_id = peer_id

    # <len: charakter 19><ProtocolName: (BitTorrent protocol)><8 reserved Bytes><info_hash (20 Bytes)><peer_id (20 Bytes)>
    # >: Big-endian B: single Byte, 19s: string with length 19, 8x: 8 times no Value, 20s String, String
    def encodeMsg(self):
        # print('handshake encode gets called')
        return struct.pack(
            Handshake.FORMAT,
            19,
            "BitTorrent protocol".encode("utf-8"),
            self.info_hash,
            self.peer_id,
        )

    @classmethod
    def decodeMsg(self, msg):  # return: Tuple(info_hash, peer_id)
        # print('handshake decode gets called')
        raw_msg = struct.unpack(self.FORMAT, msg)
        # raw_msg[0] = 19, raw_msg[1] = 'BitTorrent protocol'.encode(), raw_msg[2] = info_hash.encode, raw_msg[3] = peer_id.encode()
        info_hash = raw_msg[2]
        peer_info = raw_msg[3]
        return info_hash, peer_info


class KeepAliveMsg:
    LENGTH = 0
    FORMAT = ">i"

    def __init__(self):
        self.length = 0

    @classmethod
    def encode(cls):
        return struct.pack(cls.FORMAT, cls.LENGTH)


class ChokeMsg:
    LENGTH = 1
    FORMAT = ">iB"

    def __init__(self):
        self.id = 0

    def encode(self):
        return struct.pack(self.FORMAT, self.LENGTH, self.id)


class UnchokeMsg:
    LENGTH = 1
    FORMAT = ">iB"

    def __init__(self):
        self.id = 1

    def encode(self):
        return struct.pack(self.FORMAT, self.LENGTH, self.id)


class InterestedMsg:
    LENGTH = 1
    FORMAT = ">iB"

    def __init__(self):
        self.id = 2

    def encode(self):
        return struct.pack(self.FORMAT, self.LENGTH, self.id)


class NotInterestedMsg:
    LENGTH = 1
    FORMAT = ">iB"

    def __init__(self):
        self.id = 3

    def encode(self):
        return struct.pack(self.FORMAT, self.LENGTH, self.id)


class HaveMsg:
    LENGTH = 5
    FORMAT = ">iBi"

    def __init__(self, index):
        self.id = 4
        self.index = index

    def encode(self):
        return struct.pack(self.FORMAT, self.LENGTH, self.id, self.index)

    @classmethod
    def decode(cls, msg):
        raw_msg = struct.unpack(">i", msg)
        index = raw_msg[0]
        return index


class BitfieldMsg:
    FORMAT = ">iB"

    def __init__(self, bitfield):
        self.id = 5
        self.length = 1 + len(bitfield.tobytes())
        self.bitfield = bitfield

    def encode(self):
        res = struct.pack(self.FORMAT, self.length, self.id)
        res += self.bitfield.tobytes()
        return res

    @classmethod
    def decode(cls, msg):
        t = bitarray()
        t.frombytes(msg)
        return t


class RequestMsg:
    LENGTH = 13
    FORMAT = ">iB3i"

    def __init__(self, index, begin, length):
        self.id = 6
        self.index = index
        self.begin = begin
        self.length = length

    def encode(self):
        return struct.pack(
            self.FORMAT, self.LENGTH, self.id, self.index, self.begin, self.length
        )

    @classmethod
    def decode(cls, msg):
        raw_msg = struct.unpack(">3i", msg)
        index = raw_msg[0]
        begin = raw_msg[1]
        length = raw_msg[2]

        return index, begin, length


class PieceMsg:
    FORMAT = ">iB2i"

    def __init__(self, index, begin, block):
        self.id = 7
        self.length = 9 + len(block)
        self.index = index
        self.begin = begin
        self.block = block

    def encode(self):
        return (
            struct.pack(self.FORMAT, self.length, self.id, self.index, self.begin)
            + self.block
        )

    @classmethod
    def decode(cls, msg):
        raw_msg = struct.unpack(">2i", msg[: struct.calcsize(">2i")])
        index = raw_msg[0]
        begin = raw_msg[1]
        block = msg[struct.calcsize(">2i") :]

        return index, begin, block
