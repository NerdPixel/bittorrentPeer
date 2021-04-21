class doneException(Exception):
    def __init__(self, message):
        super().__init__(message)


class pieceNotFound(Exception):
    def __init__(self, message):
        super().__init__(message)


class conectionRefusedException(Exception):
    def __init__(self, message):
        super().__init__(message)
