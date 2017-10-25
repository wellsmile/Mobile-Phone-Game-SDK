# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals
import base64
import datetime
import json
import time

import six
from six.moves import urllib

__matrix_api_version__ = '0.0.1'
__matrix_sdk_lang__ = 'python'
__matrix_sdk_platform__ = 'common'
__matrix_sdk_version__ = '1.0.0'

class MatrixException(Exception):
    pass

class Matrix(object):
    def __init__(self, token, consumer=None, debug=False):
        self._token = token
        self._consumer = consumer or Consumer(request_timeout=3, debug=debug)

    def _now(self):
        return time.time()

    def track(self, event_name, context=None, meta=None):
        event_context = {}
        matrix_sdk_context = {
            'matrix_token': self._token,
            'matrix_timestamp': int(self._now()),
            'matrix_sdk_lang': __matrix_sdk_lang__,
            'matrix_sdk_platform': __matrix_sdk_platform__,
            'matrix_sdk_version': __matrix_sdk_version__,
            'matrix_sdk_api_version': __matrix_api_version__,
        }
        
        if context:
            event_context.update(context)
        
        if meta:
            matrix_sdk_context.update(meta)

        event = {
            'event': event_name,
            'context': event_context,
            'matrix_sdk_context': matrix_sdk_context,
        }
        
        json_message = json.dumps(event, separators=(',', ':'))
        self._consumer.send('events', json_message)

class Consumer(object):
    def __init__(self, events_url=None, people_url=None, import_url=None, request_timeout=None, debug=False):
        self._endpoints = {
            'events': events_url or 'https://matrix-api.youku-game.com/track/',
        }
        self._request_timeout = request_timeout
        self._debug = debug

    def send(self, endpoint, json_message):
        if endpoint in self._endpoints:
            self._write_request(self._endpoints[endpoint], json_message)
        else:
            raise MatrixException('No such endpoint "{0}". Valid endpoints are one of {1}'.format(endpoint, self._endpoints.keys()))

    def _write_request(self, request_url, json_message):
        data = {
            'data': base64.b64encode(json_message.encode('utf8')),
        }
        if self._debug:
            data['debug'] = True

        encoded_data = urllib.parse.urlencode(data).encode('utf8')
        try:
            request = urllib.request.Request(request_url, encoded_data)
            if self._request_timeout is not None:
                response = urllib.request.urlopen(request, timeout=self._request_timeout).read()
            else:
                response = urllib.request.urlopen(request).read()
        except urllib.error.URLError as e:
            raise six.raise_from(MatrixException(e), e)

        try:
            response = json.loads(response.decode('utf8'))
        except ValueError:
            raise MatrixException('Cannot interpret Matrix server response: {0}'.format(response))
        
        if response['status'] != 'success':
            raise MatrixException('Matrix error: {0}'.format(response['error']))

        return True

class BufferedConsumer(object):
    def __init__(self, max_size=64, events_url=None, people_url=None, import_url=None, request_timeout=None, debug=False):
        self._consumer = Consumer(events_url, people_url, import_url, request_timeout, debug)
        self._buffers = {
            'events': [],
        }
        self._max_size = min(50, max_size)

    def send(self, endpoint, json_message, api_key=None):
        if endpoint not in self._buffers:
            raise MatrixException('No such endpoint "{0}". Valid endpoints are one of {1}'.format(endpoint, self._buffers.keys()))

        buf = self._buffers[endpoint]
        buf.append(json_message)
        if len(buf) >= self._max_size:
            self._flush_endpoint(endpoint, api_key)

    def flush(self):
        for endpoint in self._buffers.keys():
            self._flush_endpoint(endpoint)

    def _flush_endpoint(self, endpoint, api_key=None):
        buf = self._buffers[endpoint]
        while buf:
            batch = buf[:self._max_size]
            batch_json = '[{0}]'.format(','.join(batch))
            try:
                self._consumer.send(endpoint, batch_json, api_key)
            except MatrixException as orig_e:
                mp_e = MatrixException(orig_e)
                mp_e.message = batch_json
                mp_e.endpoint = endpoint
                raise six.raise_from(mp_e, orig_e)
            buf = buf[self._max_size:]
        self._buffers[endpoint] = buf

if __name__ == '__main__':
    matrix = Matrix('4fbff88cb11e43bfbb4ef598032420b3')
    for i in range(2):
        print(i)
        matrix.track('user login 2', {})