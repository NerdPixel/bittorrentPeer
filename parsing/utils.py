# https://stackoverflow.com/questions/5125619/why-doesnt-list-have-safe-get-method-like-dictionary/23003811
def get(l, idx, default):
    try:
        return l[idx]
    except IndexError:
        return default
    except KeyError:
        return default


def decodeStr(x):
    return x.decode("utf-8")
