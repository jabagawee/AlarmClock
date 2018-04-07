#! /usr/bin/env python3

import mpd

KQED = 'https://streams2.kqed.org/kqedradio'


class MPDClient(object):
    def __init__(self,
                 timeout=10,
                 idletimeout=None,
                 host='localhost',
                 port=6600):
        self.timeout = timeout
        self.idletimeout = idletimeout
        self.host = host
        self.port = port

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        self.client = mpd.MPDClient()
        self.client.timeout = self.timeout
        self.client.idletimeout = self.idletimeout
        self.client.connect(self.host, self.port)
        print(self.client.mpd_version)
        print(self.client.status())

    def playKqed(self):
        self.client.clear()
        self.client.add(KQED)
        self.client.play()
        print(self.client.status())
        print(self.client.playlist())

    def stopPlaying(self):
        self.client.stop()
        print(self.client.status())

    def close(self):
        self.client.close()
        self.client.disconnect()
