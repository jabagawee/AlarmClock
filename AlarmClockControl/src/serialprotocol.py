#! /usr/bin/env python3

import datetime
import sys

from twisted.internet import reactor
from twisted.protocols.basic import LineReceiver

from .mpdclient import MPDClient

# Buttons
SLEEP_BUTTON = b'L'
SNOOZE_BUTTON = b'R'

# States
OFF = 1
SLEEP = 2
ALARM = 3
SNOOZE = 4


class SerialProtocol(LineReceiver):
    '''Arduino serial communication protocol.'''

    def __init__(self, mpd, alarms):
        super(SerialProtocol, self).__init__()
        self.mpd = mpd
        self.alarms = alarms
        self.state = OFF
        self.relay = False
        self.buzzer = False
        self.lights = False
        self.sleep_time = None
        self.snooze_time = None
        self.alarm_off_time = None
        self.alarm_time = None

    def connectionMade(self):
        print('Serial port connected.')
        self.rescheduleAlarm()
        self.sendState()

    def rescheduleAlarm(self):
        if self.alarm_time is not None and self.alarm_time.active():
            self.alarm_time.cancel()
        next_alarm = self.alarms.next_alarm()
        sys.stdout.write('Scheduling next alarm in: ' + str(next_alarm) + ' seconds\n')
        self.alarm_time = reactor.callLater(next_alarm, self.alarm_sounds)  # @UndefinedVariable

    def lineReceived(self, line):
        print('Serial RX: {0}'.format(line))
        if line[:1] == SLEEP_BUTTON:
            if self.state == OFF:
                self.state = SLEEP
                self.sleep_time = reactor.callLater(3600.0, self.everything_off)  # @UndefinedVariable
                self.relay = True
                self.buzzer = False
                self.lights = False
                sys.stdout.write('Turning on sleep\n')
                self.sendState()
                if (self.mpd):
                    with MPDClient() as client:
                        client.playKqed()
            elif self.state == SLEEP:
                if self.sleep_time is not None and self.sleep_time.active():
                    self.sleep_time.cancel()
                self.sleep_time = reactor.callLater(3600.0, self.everything_off)  # @UndefinedVariable
            elif self.state == ALARM or self.state == SNOOZE:
                self.state = OFF
                if self.alarm_off_time is not None and self.alarm_off_time.active():
                    self.alarm_off_time.cancel()
                self.alarm_off_time = None
                if self.snooze_time is not None and self.snooze_time.active():
                    self.snooze_time.cancel()
                self.snooze_time = None
                self.relay = False
                self.buzzer = False
                self.lights = False
                sys.stdout.write('Turning off alarm\n')
                self.sendState()
                if (self.mpd):
                    with MPDClient() as client:
                        client.stopPlaying()

        if line[:1] == SNOOZE_BUTTON:
            if self.state == ALARM:
                self.state = SNOOZE
                if self.snooze_time is not None and self.snooze_time.active():
                    self.snooze_time.cancel()
                self.snooze_time = reactor.callLater(540.0, self.snooze_over)  # @UndefinedVariable
                self.relay = False
                self.buzzer = False
                self.lights = False
                sys.stdout.write('Turning on snooze\n')
                self.sendState()
                if (self.mpd):
                    with MPDClient() as client:
                        client.stopPlaying()
            elif self.state == SNOOZE:
                if self.snooze_time is not None and self.snooze_time.active():
                    self.snooze_time.cancel()
                self.snooze_time = reactor.callLater(540.0, self.snooze_over)  # @UndefinedVariable
            elif self.state == SLEEP:
                self.state = OFF
                if self.sleep_time is not None and self.sleep_time.active():
                    self.sleep_time.cancel()
                self.sleep_time = None
                self.relay = False
                self.buzzer = False
                self.lights = False
                sys.stdout.write('Turning off sleep\n')
                self.sendState()
                if (self.mpd):
                    with MPDClient() as client:
                        client.stopPlaying()

    def alarm_sounds(self):
        self.rescheduleAlarm()
        if self.state != OFF:
            sys.stderr.write('Bad state ' + str(self.state) + ', expected ' + str(OFF))
            return
        self.state = ALARM
        self.alarm_off_time = reactor.callLater(3600.0, self.everything_off)  # @UndefinedVariable
        self.relay = True
        self.buzzer = True
        self.lights = True
        sys.stdout.write('Turning on alarm\n')
        self.sendState()
        if (self.mpd):
            with MPDClient() as client:
                client.playKqed()

    def snooze_over(self):
        if self.state != SNOOZE:
            sys.stderr.write('Bad state ' + str(self.state) + ', expected ' + str(SNOOZE))
            return
        self.state = ALARM
        self.snooze_time = None
        self.relay = True
        self.buzzer = True
        self.lights = True
        sys.stdout.write('Resuming alarm after snooze\n')
        self.sendState()
        if (self.mpd):
            with MPDClient() as client:
                client.playKqed()

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
        self.buzzer = False
        self.lights = False
        self.sendState()
        if (self.mpd):
            with MPDClient() as client:
                client.stopPlaying()

    def sendState(self):
        '''
        This method is exported as RPC and can be called by connected clients
        '''
        new_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(int(self.relay)) + str(int(self.buzzer)) + str(int(self.lights)) + '\n'
        sys.stdout.write('Sending time: ' + new_time)
        self.transport.write(new_time.encode('utf-8'))
