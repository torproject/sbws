import os


G_PKG_DIR = os.path.abspath(os.path.dirname(__file__))
G_INIT_FILE_MAP = [
    # (source, destination, type)
    (os.path.join(G_PKG_DIR, 'passwords.txt.example'),
     'passwords.txt', 'file'),
]


def is_initted(d):
    dotdir = os.path.join(d, '.sbws')
    if not os.path.isdir(dotdir):
        return False
    for _, fname, _ in G_INIT_FILE_MAP:
        if not os.path.exists(fname):
            return False
    return True
