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

import sys
import textwrap

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from twisted.internet import reactor
from twisted.internet import task
from twisted.internet.serialport import SerialPort
from twisted.web import server

from .alarms import Alarms
from .webinterface import WebInterface
from .serialprotocol import SerialProtocol

__all__ = []
__version__ = 0.1
__date__ = '2018-01-13'
__updated__ = '2018-01-13'

DEBUG = 0
TESTRUN = 0
PROFILE = 0


def main(argv=None):  # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_version = 'v%s' % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split('\n')[1]
    program_license = textwrap.dedent('''\
    %s

      Created by camrdale on %s.
      Copyright 2018 camrdale. All rights reserved.

      Licensed under the Apache License 2.0
      http://www.apache.org/licenses/LICENSE-2.0

      Distributed on an "AS IS" basis without warranties
      or conditions of any kind, either express or implied.

    USAGE
    ''' % (program_shortdesc, str(__date__)))

    try:
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument('-s', '--save', dest='save', type=str, default='alarmclock.crontab', help='if set, file to save alarms to [default: %(default)s]')
        parser.add_argument('-m', '--mpd', dest='mpd', action='store_true', default=False, help='enable MPD server [default: %(default)s]')
        parser.add_argument('-v', '--verbose', dest='verbose', action='count', help='set verbosity level [default: %(default)s]')
        parser.add_argument('-V', '--version', action='version', version=program_version_message)
        parser.add_argument('--web', type=int, default=8000,
                            help='Web port to use for embedded Web server. Use 0 to disable.')
        parser.add_argument(dest='port', help='serial port to connect to [default: %(default)s]', nargs='?', default='COM3')

        args = parser.parse_args()

        print('Using Twisted reactor {0}'.format(reactor.__class__))  # @UndefinedVariable

        alarms = Alarms(args.save)

        serialProtocol = SerialProtocol(args.mpd, alarms)

        # Create embedded web server to manage the alarms.
        if args.web:
            reactor.listenTCP(args.web, server.Site(WebInterface(alarms, serialProtocol)))  # @UndefinedVariable

        print('About to open serial port {0} [{1} baud] ..'.format(args.port, 9600))
        try:
            SerialPort(serialProtocol, args.port, reactor, baudrate=9600)
        except Exception as e:
            print('Could not open serial port: {0}'.format(e))
            return 1

        loop = task.LoopingCall(serialProtocol.sendState)

        def cbLoopDone(result):
            '''Called when loop was stopped with success.'''
            print('Loop done: ' + result)

        def ebLoopFailed(failure):
            '''Called when loop execution failed.'''
            print(failure.getBriefTraceback())

        # Start looping every 10 seconds.
        loopDeferred = loop.start(10.0)

        # Add callbacks for stop and failure.
        loopDeferred.addCallback(cbLoopDone)
        loopDeferred.addErrback(ebLoopFailed)

        # start the component and the Twisted reactor ..
        reactor.run()  # @UndefinedVariable

        return 0
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    if DEBUG:
        sys.argv.append('-h')
        sys.argv.append('-v')
        sys.argv.append('-r')
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'alarmclock_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open('profile_stats.txt', 'wb')
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())
