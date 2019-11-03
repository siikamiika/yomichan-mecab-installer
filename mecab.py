#!/usr/bin/python3 -u

# Copyright (C) 2019 siikamiika
# Author: siikamiika
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import sys
import os
import re
import struct
import subprocess
import threading
import queue

DIR = os.path.realpath(os.path.dirname(__file__))


def get_message():
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        sys.exit(0)
    message_length = struct.unpack('@I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)


def send_message(message_content):
    encoded_content = json.dumps(message_content).encode('utf-8')
    encoded_length = struct.pack('@I', len(encoded_content))
    sys.stdout.buffer.write(encoded_length)
    sys.stdout.buffer.write(encoded_content)
    sys.stdout.buffer.flush()


class Mecab:
    output_formats = {
        'ipadic': ['pos', 'pos2', '_', '_', '_', '_', 'expression', 'reading', 'pron'],
        'ipadic-neologd': ['pos', 'pos2', '_', '_', '_', '_', 'expression', 'reading', 'pron'],
        'unidic-mecab-translate': [
            'pos', 'pos2', 'pos3', 'pos4', 'inflection_type', 'inflection_form',
            'reading', 'expression', '_', 'pron'
        ],
    }
    skip_patt = r'[\s・]'

    def __init__(self, output_format):
        self.output_format = Mecab.output_formats[output_format]
        args = ['mecab', '-d', os.path.join(DIR, 'data', output_format), '-r', os.path.join(DIR, 'mecabrc')]
        self.process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            bufsize=1
        )
        self.process_output_queue = queue.Queue()

        self.stdout_thread = threading.Thread(target=self.bg_handle_stdout)
        self.stdout_thread.daemon = True
        self.stdout_thread.start()

    def parse(self, text):
        parsed_lines = []
        for text_line in text.splitlines():
            parsed_line = []
            for text_line_part in re.findall(r'{0}|.*?(?={0})|.*'.format(Mecab.skip_patt), text_line):
                if re.match(Mecab.skip_patt, text_line_part):
                    parsed_line.append(self.gen_dummy_output(text_line_part))
                    continue
                self.process.stdin.write((text_line_part + '\n').encode('utf-8'))
                self.process.stdin.flush()
                for output_part in iter(self.process_output_queue.get, 'EOS'):
                    parsed_part = {}
                    try:
                        parsed_part['source'], output_part_info = output_part.split('\t', 1)
                        output_part_info_parsed = ['' if i == '*'
                                                   else re.sub(Mecab.skip_patt, '', i.split('-')[0])
                                                   for i in output_part_info.split(',')]
                        parsed_part.update(zip(self.output_format, output_part_info_parsed))
                        parsed_line.append(parsed_part)
                    except Exception as e:
                        print(e, file=sys.stderr)
            parsed_lines.append(parsed_line)
        return parsed_lines

    def gen_dummy_output(self, text):
        output = {'source': text, 'expression': text, 'reading': text}
        for key in self.output_format:
            if key not in output:
                output[key] = ''
        return output

    def bg_handle_stdout(self):
        for line in iter(self.process.stdout.readline, b''):
            self.process_output_queue.put(line.decode('utf-8').strip())
        self.process.stdout.close()


def main():
    mecab = Mecab('ipadic')
    while True:
        msg = get_message()
        if msg['action'] == 'parse_text':
            text = msg['params']['text']
            response = mecab.parse(text)
            send_message({
                'sequence': msg['sequence'],
                'data': response,
            })

if __name__ == '__main__':
    main()