#!/usr/bin/env python3
# encoding: utf-8
'''
alarmclock -- shortdesc

alarmclock is a script to control an Arduino/Raspberry Pi alarm clock.

@author:     camrdale

@copyright:  2018 camrdale. All rights reserved.

@license:    Apache License 2.0

@contact:    camrdale@gmail.com
'''

import datetime
import mpd
import os
import sys

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from twisted.internet import reactor
from twisted.internet import task
from twisted.internet.serialport import SerialPort
from twisted.protocols.basic import LineReceiver
from twisted.web import server
from twisted.web.server import resource

__all__ = []
__version__ = 0.1
__date__ = '2018-01-13'
__updated__ = '2018-01-13'

DEBUG = 0
TESTRUN = 0
PROFILE = 0
KQED = 'https://streams2.kqed.org/kqedradio'

# Buttons
SLEEP_BUTTON = b'L'
SNOOZE_BUTTON = b'R'

# States
OFF = 1
SLEEP = 2
ALARM = 3
SNOOZE = 4


def mpdConnect():
    client = mpd.MPDClient()
    client.timeout = 10
    client.idletimeout = None
    client.connect("localhost", 6600)
    print(client.mpd_version)
    print(client.status())
    return client

def playKqed(client):
    client.clear()
    client.add(KQED)
    client.play()
    print(client.status())
    print(client.playlist())
    
def stopPlaying(client):
    client.stop()
    print(client.status())

def mpdClose(client):
    client.close()
    client.disconnect()  


class SerialProtocol(LineReceiver):
    """
    Arduino serial communication protocol.
    """
    
    def __init__(self, mpd, alarm):
        super(SerialProtocol, self).__init__()
        self.mpd = mpd
        self.alarm = alarm
        self.state = OFF
        self.relay = False
        self.buzzer = False
        self.lights = False
        self.sleep_time = None
        self.snooze_time = None
        self.alarm_off_time = None
        self.alarm_time = None

    def next_alarm(self):
        current_time = datetime.datetime.now()
        next_alarm_day = current_time
        alarm_time = next_alarm_day.replace(hour=self.alarm.hour, minute=self.alarm.minute, second=self.alarm.second)
        delta = alarm_time - current_time
        if delta < datetime.timedelta(seconds=60):
            next_alarm_day = current_time + datetime.timedelta(days=1)
            alarm_time = next_alarm_day.replace(hour=self.alarm.hour, minute=self.alarm.minute, second=self.alarm.second)
            delta = alarm_time - current_time
        return delta
        
    def connectionMade(self):
        print('Serial port connected.')
        self.alarm_time = reactor.callLater(float(self.next_alarm().total_seconds()), self.alarm_sounds)
        self.sendState()

    def lineReceived(self, line):
        print("Serial RX: {0}".format(line))
        if line[:1] == SLEEP_BUTTON:
            if self.state == OFF:
                self.state = SLEEP
                self.sleep_time = reactor.callLater(3600.0, self.everything_off)
                self.relay = True
                self.lights = False
                sys.stdout.write('Turning on sleep\n')
                self.sendState()
                if (self.mpd):
                    client = mpdConnect()
                    playKqed(client)
                    mpdClose(client)
            elif self.state == SLEEP:
                if self.sleep_time is not None and self.sleep_time.active():
                    self.sleep_time.cancel()
                self.sleep_time = reactor.callLater(3600.0, self.everything_off)
            elif self.state == ALARM or self.state == SNOOZE:
                self.state = OFF
                if self.alarm_off_time is not None and self.alarm_off_time.active():
                    self.alarm_off_time.cancel()
                self.alarm_off_time = None
                if self.snooze_time is not None and self.snooze_time.active():
                    self.snooze_time.cancel()
                self.snooze_time = None
                self.relay = False
                self.lights = False
                sys.stdout.write('Turning off alarm\n')
                self.sendState()
                if (self.mpd):
                    client = mpdConnect()
                    stopPlaying(client)
                    mpdClose(client)
                
        if line[:1] == SNOOZE_BUTTON:
            if self.state == ALARM:
                self.state = SNOOZE
                if self.snooze_time is not None and self.snooze_time.active():
                    self.snooze_time.cancel()
                self.snooze_time = reactor.callLater(540.0, self.snooze_over)
                self.relay = False
                self.lights = False
                sys.stdout.write('Turning on snooze\n')
                self.sendState()
                if (self.mpd):
                    client = mpdConnect()
                    stopPlaying(client)
                    mpdClose(client)
            elif self.state == SNOOZE:
                if self.snooze_time is not None and self.snooze_time.active():
                    self.snooze_time.cancel()
                self.snooze_time = reactor.callLater(540.0, self.snooze_over)
            elif self.state == SLEEP:
                self.state = OFF
                if self.sleep_time is not None and self.sleep_time.active():
                    self.sleep_time.cancel()
                self.sleep_time = None
                self.relay = False
                self.lights = False
                sys.stdout.write('Turning off sleep\n')
                self.sendState()
                if (self.mpd):
                    client = mpdConnect()
                    stopPlaying(client)
                    mpdClose(client)

    def alarm_sounds(self):
        self.alarm_time = reactor.callLater(self.next_alarm().total_seconds(), self.alarm_sounds)
        if self.state != OFF:
            sys.stderr.write('Bad state ' + str(self.state) + ', expected ' + str(OFF))
            return
        self.state = ALARM
        self.alarm_off_time = reactor.callLater(3600.0, self.everything_off)
        self.relay = True
        self.lights = True
        sys.stdout.write('Turning on alarm\n')
        self.sendState()
        if (self.mpd):
            client = mpdConnect()
            playKqed(client)
            mpdClose(client)

    def snooze_over(self):
        if self.state != SNOOZE:
            sys.stderr.write('Bad state ' + str(self.state) + ', expected ' + str(SNOOZE))
            return
        self.state = ALARM
        self.snooze_time = None
        self.relay = True
        self.lights = True
        sys.stdout.write('Resuming alarm after snooze\n')
        self.sendState()
        if (self.mpd):
            client = mpdConnect()
            playKqed(client)
            mpdClose(client)

    def everything_off(self):
        if self.state == SLEEP:
            self.sleep_time = None
            sys.stdout.write('Turning off radio after sleep\n')
        elif self.state == SNOOZE:
            if self.snooze_time is not None and self.snooze_time.active():
                self.snooze_time.cancel()
            self.snooze_time = None
            self.alarm_off_time = None
            sys.stdout.write('Turning off alarm\n')
        elif self.state == ALARM:
            self.alarm_off_time = None
            sys.stdout.write('Turning off alarm\n')
        else:
            sys.stderr.write('Bad state ' + str(self.state) + ', expected ' + str(SLEEP))
            return
        self.state = OFF
        self.relay = False
        self.lights = False
        self.sendState()
        if (self.mpd):
            client = mpdConnect()
            stopPlaying(client)
            mpdClose(client)

    def sendState(self):
        """
        This method is exported as RPC and can be called by connected clients
        """
        new_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(int(self.relay)) + str(int(self.buzzer)) + str(int(self.lights)) + '\n'
        sys.stdout.write('Sending time: ' + new_time)
        self.transport.write(new_time.encode('utf-8'))


class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg


class WebInterface(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        return "<html>Hello, world!</html>".encode('utf-8')


def main(argv=None): # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Created by camrdale on %s.
  Copyright 2018 camrdale. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-H", "--hour", dest="hour", type=int, default=8, help="alarm hour (24-hour clock) [default: %(default)s]")
        parser.add_argument("-M", "--minute", dest="minute", type=int, default=30, help="alarm minute [default: %(default)s]")
        parser.add_argument("-m", "--mpd", dest="mpd", action="store_true", default=False, help="enable MPD server [default: %(default)s]")
        parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %(default)s]")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)
        parser.add_argument("--web", type=int, default=8000,
                            help='Web port to use for embedded Web server. Use 0 to disable.')
        parser.add_argument(dest="port", help="serial port to connect to [default: %(default)s]", nargs='?', default="COM3")

        # Process arguments
        args = parser.parse_args()

        #verbose = args.verbose

        #if verbose > 0:
        #    print("Verbose mode on")

        print("Using Twisted reactor {0}".format(reactor.__class__))
    
        # create embedded web server for static files
        if args.web:
            reactor.listenTCP(args.web, server.Site(WebInterface()))
    
        serialProtocol = SerialProtocol(args.mpd, datetime.time(args.hour, args.minute))

        print('About to open serial port {0} [{1} baud] ..'.format(args.port, 9600))
        try:
            serialPort = SerialPort(serialProtocol, args.port, reactor, baudrate=9600)
        except Exception as e:
            print('Could not open serial port: {0}'.format(e))
            return 1

        loop = task.LoopingCall(serialProtocol.sendState)

        def cbLoopDone(result):
            """
            Called when loop was stopped with success.
            """
            print("Loop done: " + result)
        
        def ebLoopFailed(failure):
            """
            Called when loop execution failed.
            """
            print(failure.getBriefTraceback())
            
        # Start looping every 10 seconds.
        loopDeferred = loop.start(10.0)
        
        # Add callbacks for stop and failure.
        loopDeferred.addCallback(cbLoopDone)
        loopDeferred.addErrback(ebLoopFailed)
    
        # start the component and the Twisted reactor ..
        reactor.run()
        
        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
#     except Exception as e:
#         if DEBUG or TESTRUN:
#             raise(e)
#         indent = len(program_name) * " "
#         sys.stderr.write(program_name + ": " + repr(e) + "\n")
#         sys.stderr.write(indent + "  for help use --help")
#         return 2

if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-h")
        sys.argv.append("-v")
        sys.argv.append("-r")
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'alarmclock_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())