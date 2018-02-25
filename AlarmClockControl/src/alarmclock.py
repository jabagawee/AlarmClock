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
import platform
import serial
import sys
import time

import os

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

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

def alarmclock(port, mpd, alarm):
    state = OFF
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = 9600
    ser.timeout = 1
    if platform.system() == 'Windows':
        # Disable the DTR on Windows so the Arduino doesn't reset
        # On Linux, the serial port should be configured to diable
        # DTR with:  stty -F /dev/ttyACM0 -hupcl
        ser.setDTR(False)
    ser.open()
    
    time.sleep(2)
    next_update = 0;
    last_update = datetime.datetime.now()
    sleep_time = None
    snooze_time = None
    alarm_off_time = None
    relay = False
    buzzer = False
    lights = False
    
    while 1:
        ser_output = ser.readline()
        if ser_output:
            sys.stdout.write('Received: %s\n' % (ser_output,))
            if ser_output[:1] == SLEEP_BUTTON:
                if state == OFF:
                    state = SLEEP
                    sleep_time = datetime.datetime.now() + datetime.timedelta(hours=1)
                    relay = True
                    lights = False
                    new_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(int(relay)) + str(int(buzzer)) + str(int(lights)) + '\n'
                    sys.stdout.write('Turning on sleep: ' + new_time)
                    ser.write(new_time.encode('utf-8'))
                    if (mpd):
                        client = mpdConnect()
                        playKqed(client)
                        mpdClose(client)
                elif state == SLEEP:
                    sleep_time = datetime.datetime.now() + datetime.timedelta(hours=1)
                elif state == ALARM or state == SNOOZE:
                    state = OFF
                    alarm_off_time = None
                    relay = False
                    lights = False
                    new_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(int(relay)) + str(int(buzzer)) + str(int(lights)) + '\n'
                    sys.stdout.write('Turning off alarm: ' + new_time)
                    ser.write(new_time.encode('utf-8'))
                    if (mpd):
                        client = mpdConnect()
                        stopPlaying(client)
                        mpdClose(client)
                    
            if ser_output[:1] == SNOOZE_BUTTON:
                if state == ALARM:
                    state = SNOOZE
                    snooze_time = datetime.datetime.now() + datetime.timedelta(minutes=9)
                    relay = False
                    lights = False
                    new_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(int(relay)) + str(int(buzzer)) + str(int(lights)) + '\n'
                    sys.stdout.write('Turning on snooze: ' + new_time)
                    ser.write(new_time.encode('utf-8'))
                    if (mpd):
                        client = mpdConnect()
                        stopPlaying(client)
                        mpdClose(client)
                elif state == SNOOZE:
                    snooze_time = datetime.datetime.now() + datetime.timedelta(minutes=9)
                elif state == SLEEP:
                    state = OFF
                    sleep_time = None
                    relay = False
                    lights = False
                    new_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(int(relay)) + str(int(buzzer)) + str(int(lights)) + '\n'
                    sys.stdout.write('Turning off sleep: ' + new_time)
                    ser.write(new_time.encode('utf-8'))
                    if (mpd):
                        client = mpdConnect()
                        stopPlaying(client)
                        mpdClose(client)

        else:
            current_time = datetime.datetime.now()
            if state == OFF:
                alarm_time = current_time.replace(hour=alarm.hour, minute=alarm.minute, second=alarm.second)
                if last_update < alarm_time and alarm_time <= current_time:
                    state = ALARM
                    alarm_off_time = datetime.datetime.now() + datetime.timedelta(hours=1)
                    relay = True
                    lights = True
                    new_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(int(relay)) + str(int(buzzer)) + str(int(lights)) + '\n'
                    sys.stdout.write('Turning on alarm: ' + new_time)
                    ser.write(new_time.encode('utf-8'))
                    if (mpd):
                        client = mpdConnect()
                        playKqed(client)
                        mpdClose(client)
            elif state == SLEEP:
                if last_update < sleep_time and sleep_time <= current_time:
                    state = OFF
                    sleep_time = None
                    relay = False
                    lights = False
                    new_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(int(relay)) + str(int(buzzer)) + str(int(lights)) + '\n'
                    sys.stdout.write('Turning off after sleep: ' + new_time)
                    ser.write(new_time.encode('utf-8'))
                    if (mpd):
                        client = mpdConnect()
                        stopPlaying(client)
                        mpdClose(client)
            elif state == SNOOZE:
                if last_update < snooze_time and snooze_time <= current_time:
                    state = ALARM
                    snooze_time = None
                    relay = True
                    lights = True
                    new_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(int(relay)) + str(int(buzzer)) + str(int(lights)) + '\n'
                    sys.stdout.write('Resuming alarm after snooze: ' + new_time)
                    ser.write(new_time.encode('utf-8'))
                    if (mpd):
                        client = mpdConnect()
                        playKqed(client)
                        mpdClose(client)
                if last_update < alarm_off_time and alarm_off_time <= current_time:
                    state = OFF
                    snooze_time = None
                    alarm_off_time = None
                    relay = False
                    lights = False
                    new_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(int(relay)) + str(int(buzzer)) + str(int(lights)) + '\n'
                    sys.stdout.write('Turning off alarm: ' + new_time)
                    ser.write(new_time.encode('utf-8'))
                    if (mpd):
                        client = mpdConnect()
                        stopPlaying(client)
                        mpdClose(client)
            elif state == ALARM:
                if last_update < alarm_off_time and alarm_off_time <= current_time:
                    state = OFF
                    alarm_off_time = None
                    relay = False
                    lights = False
                    new_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(int(relay)) + str(int(buzzer)) + str(int(lights)) + '\n'
                    sys.stdout.write('Turning off alarm: ' + new_time)
                    ser.write(new_time.encode('utf-8'))
                    if (mpd):
                        client = mpdConnect()
                        stopPlaying(client)
                        mpdClose(client)
            last_update = current_time
            
        
        if next_update <= 0:
            new_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(int(relay)) + str(int(buzzer)) + str(int(lights)) + '\n'
            sys.stdout.write('Updating to new time: ' + new_time)
            ser.write(new_time.encode('utf-8'))
            next_update = 60
    
        next_update = next_update - 1
    
    ser.close()

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg

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
        parser.add_argument(dest="port", help="serial port to connect to [default: %(default)s]", nargs='?', default="COM3")

        # Process arguments
        args = parser.parse_args()

        #verbose = args.verbose

        #if verbose > 0:
        #    print("Verbose mode on")

        alarmclock(args.port, args.mpd, datetime.time(args.hour, args.minute))
        
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