import hashlib


class ByteStorage:
    def __init__(self, chunks):
        self.chunks = chunks  # Array expected in proper order of chunks
        self.chunkMapping = dict()  # stores parts for corresponding chunks
        self.sha1 = hashlib.sha1()  # sha1 for checking part validity

    def addPart(self, chunk, part):
        if self.checkPartValidty(chunk, part):
            self.chunkMapping[chunk] = part
            if len(self.chunkMapping) == len(self.chunks):
                return True, True  # When we are finished
            else:
                return True, False  # When parts are missing
        else:
            return False  # Part is not valid! Rejecting!

    def checkPartValidty(self, chunk, part):
        assert chunk == self.hasher(part)

    def exportTorrentContent(
            self):  # Exports all bytes in proper order, if all parts have been successfully downloaded and are valid
        torrentContent = ""
        for chunk in self.chunks:
            if chunk in self.chunkMapping:
                torrentContent += self.chunkMapping[chunk]
            else:
                return False  # Not all parts have been downloaded
        return torrentContent

    def reportMissingParts(self):
        missing = []
        for chunk in self.chunks:
            if chunk not in self.chunkMapping:
                missing.push(chunk)
        return missing
