import os

from parsing.utils import decodeStr

class File:
    folderPath: str
    filename: str
    md5sum: str
    length: int

    def __init__(self, save_path, path, md5sum, length):
        path_converted = list(map(decodeStr, path))
        path_converted.insert(0, save_path)

        self.filename = path_converted.pop()
        self.folderPath = "/".join(path_converted) + "/"
        self.md5sum = md5sum
        self.length = length

        self.initFolderStructure()

    def getFilepath(self):
        return self.folderPath + self.filename

    def initFolderStructure(self):
        if not os.path.exists(self.folderPath):
            os.makedirs(self.folderPath)

