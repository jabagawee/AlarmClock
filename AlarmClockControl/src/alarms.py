#! /usr/bin/env python3

import datetime
import sys

from crontab import CronTab


class _Alarm(object):
    '''A single (possibly recurring) alarm.'''

    def __init__(self, crontab):
        self._crontab = crontab
        self._alarm = CronTab(crontab)

    def next(self, now=None):
        return self._alarm.next(now=now, default_utc=False)

    def get_crontab(self):
        return self._crontab


class Alarms(object):
    '''Container for multiple recurring alarms.'''

    def __init__(self, save_path):
        self._save_path = None
        self._alarms = []
        if save_path != '':
            self._save_path = save_path
            self._alarms = self._load_alarms()
            sys.stdout.write('Loaded %s alarms from save file %s:\n' %
                             (len(self._alarms), self._save_path))
            for alarm in self._alarms:
                sys.stdout.write('  %s\n' % alarm.get_crontab())

    def reschedule_all(self, crontabs):
        crontabs = [crontab.strip() for crontab in crontabs]

        sys.stdout.write('Rescheduling new alarms:\n')
        for crontab in crontabs:
            sys.stdout.write('  %s\n' % crontab)

        self._alarms = [_Alarm(crontab) for crontab in crontabs]
        if self._save_path:
            self._save_alarms()

    def next_alarm(self):
        return min([alarm.next() for alarm in self._alarms])

    def next_alarms(self, n, now=None):
        if now is None:
            now = datetime.datetime.now()
        result = []

        for _ in range(n):
            now += datetime.timedelta(seconds=min(
                alarm.next(now=now)
                for alarm in self._alarms))
            result.append(now)

        return result

    def __len__(self):
        return len(self._alarms)

    def get_crontabs(self):
        return [alarm.get_crontab() for alarm in self._alarms]

    def _load_alarms(self):
        assert self._save_path, 'self._save_path should be set'
        try:
            with open(self._save_path) as f:
                return [_Alarm(line.strip()) for line in f.readlines() if not line.startswith('#')]
        except Exception:
            sys.stdout.write('Ignoring missing save file: %s\n' % self._save_path)

    def _save_alarms(self):
        try:
            with open(self._save_path, 'w') as f:
                f.write('# m h dom mon dow\n')
                for crontab in self.get_crontabs():
                    f.write(crontab + '\n')
            sys.stdout.write('Wrote %s alarms to save file %s\n' %
                             (len(self._alarms), self._save_path))
        except Exception:
            sys.stderr.write('Failed to write to save file: %s\n' % self._save_path)
