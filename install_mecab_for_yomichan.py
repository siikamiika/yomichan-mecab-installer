#!/usr/bin/env python3

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

import sys
import os
import json
import copy
import urllib.request
import zipfile

DIR = os.path.realpath(os.path.dirname(__file__))

NAME = 'yomichan_mecab'

MANIFEST_TEMPLATE = {
    'name': 'yomichan_mecab',
    'description': 'MeCab for Yomichan',
    'type': 'stdio',
}

BROWSER_DATA = {
    'firefox': {
        'extension_id_key': 'allowed_extensions',
        'extension_ids': ['alex@foosoft.net'],
    },
    'chrome': {
        'extension_id_key': 'allowed_origins',
        'extension_ids': ['chrome-extension://ogmnaimimemjmbakcfefmnahgdfhfami/'],
    },
    'chromium': {
        'extension_id_key': 'allowed_origins',
        'extension_ids': ['chrome-extension://ogmnaimimemjmbakcfefmnahgdfhfami/'],
    },
}

PLATFORM_DATA = {
    'linux': {
        'platform_aliases': ['linux', 'linux2', 'riscos', 'freebsd7', 'freebsd8', 'freebsdN', 'openbsd6'],
        'manifest_install_data': {
            'firefox': {
                'methods': ['file'],
                'path': os.path.expanduser('~/.mozilla/native-messaging-hosts/'),
            },
            'chrome': {
                'methods': ['file'],
                'path': os.path.expanduser('~/.config/google-chrome/NativeMessagingHosts/'),
            },
            'chromium': {
                'methods': ['file'],
                'path': os.path.expanduser('~/.config/chromium/NativeMessagingHosts/'),
            },
        }
    },
    'windows': {
        'platform_aliases': ['win32', 'cygwin'],
        'manifest_install_data': {
            'firefox': {
                'methods': ['file', 'registry'],
                'path': DIR,
                'registry_path': 'SOFTWARE\\Mozilla\\NativeMessagingHosts',
            },
            'chrome': {
                'methods': ['file', 'registry'],
                'path': DIR,
                'registry_path': 'SOFTWARE\\Google\\Chrome\\NativeMessagingHosts',
            },
            'chromium': {
                'methods': ['file', 'registry'],
                'path': DIR,
            },
        }
    },
    'mac': {
        'platform_aliases': ['darwin'],
        'manifest_install_data': {
            'firefox': {
                'methods': ['file'],
                'path': os.path.expanduser('~/Library/Application Support/Mozilla/NativeMessagingHosts/'),
            },
            'chrome': {
                'methods': ['file'],
                'path': os.path.expanduser('~/Library/Application Support/Google/Chrome/NativeMessagingHosts/'),
            },
            'chromium': {
                'methods': ['file'],
                'path': os.path.expanduser('~/Library/Application Support/Chromium/NativeMessagingHosts/'),
            },
        }
    },
}

DICTIONARY_DATA = {
    'ipadic': {
        'url': 'https://github.com/siikamiika/yomichan-mecab-installer/releases/download/ipadic-1/ipadic.zip',
        'compression': 'zip',
        'size': '51M',
        'description': 'A basic dictionary',
    },
    'unidic-mecab-translate': {
        'url': 'https://github.com/siikamiika/unidic-mecab-translate/releases/download/1.3/unidic-mecab-translate-1.3.zip',
        'compression': 'zip',
        'size': '191M',
        'description': 'A dictionary that prefers shorter words to longer ones, is usually more accurate, and shows pronunciation instead of reading',
    }
}

def platform_data_get():
    for platform_name in PLATFORM_DATA:
        data = copy.deepcopy(PLATFORM_DATA[platform_name])
        data['platform'] = platform_name
        if sys.platform in data['platform_aliases']:
            return data
        raise Exception('Unsupported platform: {}'.format(sys.platform))

def manifest_get(browser, messaging_host_path, additional_ids=[]):
    manifest = copy.deepcopy(MANIFEST_TEMPLATE)
    data = BROWSER_DATA[browser]
    manifest['path'] = messaging_host_path
    manifest[data['extension_id_key']] = []
    for extension_id in data['extension_ids'] + additional_ids:
        manifest[data['extension_id_key']].append(extension_id)
    return json.dumps(manifest, indent=4)

def manifest_install_file(manifest, path):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, MANIFEST_FILENAME + '.json'), 'w') as f:
        f.write(manifest)

def download_dict(url, compression):
    print('Downloading...')
    os.makedirs('data', exist_ok=True)
    tmp_path, _ = urllib.request.urlretrieve(url)
    if compression == 'zip':
        extract_zip(tmp_path, 'data')
    print('Done!')

def extract_zip(zip_path, extract_path):
    print('Extracting...')
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_path)


def main():
    platform_data = platform_data_get()

    # choose browser
    browsers = list(BROWSER_DATA)
    for i, browser in enumerate(browsers):
        print('{}: {}'.format(i + 1, browser))
    browser = browsers[int(input('Choose browser: ')) - 1]

    # generate manifest
    print()
    print('Using default Yomichan extension ID for {}.'.format(browser))
    print('Add more extension IDs, or press enter to continue')
    additional_extension_ids = []
    while True:
        extension_id = input('Extension ID: ')
        if not extension_id:
            break
        additional_extension_ids.append(extension_id)
    script_path = os.path.join(DIR, 'mecab.py')
    if platform_data['platform'] == 'windows':
        script_path = os.path.join(DIR, 'mecab.bat')
        with open(script_path, 'w') as f:
            f.write('@echo off\n\npython -u "{}"'.format(
                script_path.replace('\\', '\\\\')
            ))
    manifest = manifest_get(browser, script_path, additional_extension_ids)
    manifest_install_data = platform_data['manifest_install_data'][browser]
    for method in manifest_install_data['methods']:
        if method == 'file':
            manifest_install_file(manifest, manifest_install_data['path'])
        if method == 'registry':
            import winreg
            winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                             manifest_install_data['registry_path'])
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                          manifest_install_data['registry_path'],
                                          0, winreg.KEY_WRITE)
            winreg.SetValueEx(registry_key, NAME, 0, winreg.REG_SZ,
                              manifest_install_data['path'])
            winreg.CloseKey(registry_key)

    # install dictionaries
    print()
    if input('Install a MeCab dictionary? (Y/n): ').lower() in ['', 'y']:
        mecab_dictionaries = list(DICTIONARY_DATA)
        for i, dict_name in enumerate(mecab_dictionaries):
            dict_data = DICTIONARY_DATA[dict_name]
            print('{}: {} [{}] - {}'.format(i + 1, dict_name, dict_data['size'], dict_data['description']))
        dictionary = mecab_dictionaries[int(input('Choose dictionary: ')) - 1]
        dictionary_data = DICTIONARY_DATA[dictionary]
        download_dict(dictionary_data['url'], 'zip')


if __name__ == '__main__':
    main()
