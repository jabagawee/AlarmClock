#! /usr/bin/env python3

import datetime

from twisted.web import resource

NUM_ALARMS_DISPLAY = 10


class WebInterface(resource.Resource):
    isLeaf = True

    def __init__(self, alarms, serialProtocol):
        super(WebInterface, self).__init__()
        self._alarms = alarms
        self._serialProtocol = serialProtocol

    def render_GET(self, request):
        return self._render_form(
            int(request.args['showalarms'.encode('utf-8')][0].decode('utf-8'))
            if 'showalarms'.encode('utf-8') in request.args.keys()
            else NUM_ALARMS_DISPLAY)

    def _render_form(self, num_alarms_display):
        page = ['<html>',
                '<head>',
                '  <script>',
                'var nextRowId = %s;' % self._alarms.num_alarms(),
                '''\
                function appendRow() {
                var ul = document.getElementById("alarms");

                var li = document.createElement("li");
                li.id = "row" + nextRowId;

                var input = document.createElement("input");
                input.type = "text";
                input.name = "alarm" + nextRowId;
                input.value = "* * * * *";
                li.appendChild(input);

                var button = document.createElement("input");
                button.type = "button";
                button.value = "Delete";
                button.setAttribute("onClick", "deleteRow(" + nextRowId + ")");
                li.appendChild(button);

                ul.appendChild(li);
                nextRowId = nextRowId + 1;
                }

                function deleteRow(rowNum) {
                var row = document.getElementById("row" + rowNum);
                row.parentNode.removeChild(row);
                }
                ''',
                '  </script>',
                '</head>',
                '<body>',
                '  <p>Current alarms:</p>',
                '  <form method="POST">',
                '  <ul id="alarms">']
        i = 0
        for alarm in self._alarms.get_alarm_crontabs():
            page.append('    <li id="row%s"><input type="text" name="alarm%s" value="%s"><input type="button" value="Delete" onClick="deleteRow(%s)"></li>' % (i, i, alarm, i))
            i += 1

        page.extend([
            '  </ul>',
            '  <input type="button" value="Add Alarm" onClick="appendRow()">',
            '  <input type="submit" value="Submit">',
            '  </form>'])

        now = datetime.datetime.now()
        page.append('  <p>Current time: %s</p>' % now.strftime('%I:%M:%S %p %A, %B %d, %Y'))

        page.extend([
            '  <p>Next %d alarms:</p>' % num_alarms_display,
            '  <ul>'])

        for alarm in self._alarms.next_alarms(num_alarms_display, now=now):
            page.append('    <li>%s</li>' % alarm.strftime('%I:%M:%S %p %A, %B %d, %Y'))
        page.extend([
            '  </ul>',
            '<p><a href="?showalarms=%d">Show %d more alarms</a></p>' %
            (num_alarms_display + NUM_ALARMS_DISPLAY, NUM_ALARMS_DISPLAY),
            '</body></html>',
            '</body></html>'])
        return ('\n'.join(page)).encode('utf-8')

    def render_POST(self, request):
        new_alarms = [request.args[arg][0].decode('utf-8')
                      for arg in request.args.keys()
                      if arg.startswith('alarm'.encode('utf-8'))]
        self._alarms.reschedule_all(new_alarms)
        self._serialProtocol.rescheduleAlarm()
        return self._render_form()
