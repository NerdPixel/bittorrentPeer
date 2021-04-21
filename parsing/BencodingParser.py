import hashlib
import io


class BencodingParser:
    def __init__(self, path=None, text=None):
        if text:
            self.file = io.BytesIO(text)
            self.file1 = io.BytesIO(text)
        else:
            self.file = open(path, "rb")
            self.file1 = open(path, "rb")

        self.info_start = 0
        self.dict_ends = []
        self.info_hash = ""

    def parse(self):
        return self.parseToken()

    def parseNumber(self, delimiter=b"e"):
        num = bytearray()
        while True:
            b = self.file.read(1)
            if b == delimiter:
                break
            else:
                num.append(b[0])
        num_str = num.decode("utf-8")
        return int(num_str)

    def parseInt(self):
        return self.parseNumber()

    def parseDict(self):
        ret = {}
        is_info = False
        while True:
            key_bytes = self.parseToken()
            if key_bytes == b"info":
                is_info = True
                self.info_start = self.file.tell()
            if key_bytes == None:
                break

            ret[key_bytes.decode("utf-8")] = self.parseToken()
        self.dict_ends.append(self.file.tell())
        if is_info == True:
            info_end = self.dict_ends[len(self.dict_ends) - 2]
            self.file1.seek(self.info_start, 0)
            res = self.file1.read(info_end - self.info_start)
            self.hash_info(res)
        return ret

    def hash_info(self, message):
        hashed = hashlib.sha1(message)
        self.info_hash = hashed.digest()
        # print(hashed.hexdigest())

    def parseList(self):
        ret = []
        while True:
            value = self.parseToken()
            if value == None:
                break

            ret.append(value)
        return ret

    def parseString(self):
        self.file.seek(self.file.tell() - 1)  # go back one step to read whole number
        length = self.parseNumber(delimiter=b":")
        return self.file.read(length)

    def parseToken(self):
        b = self.file.read(1)

        if b == b"i":
            return self.parseInt()
        elif b == b"l":
            return self.parseList()
        elif b == b"d":
            return self.parseDict()
        elif b"0" <= b <= b"9":
            return self.parseString()
        elif b == b"e":
            return None


# b = BencodingParser("../cli/big-buck-bunny.torrent")
# b = BencodingParser("../cli/test.torrent")
# b.parse()
