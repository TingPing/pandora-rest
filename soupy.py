"""
Provides slightly more pythonic bindings to libsoup
"""

__license__ = 'GPL-3.0+'

import asyncio
import enum
import gi
gi.require_version('Soup', '2.4')
from gi.repository import Soup
import json
from typing import Awaitable, Dict


class SoupException(Exception):
    def __init__(self, message: Soup.Message):
        # self.status_code = message.props.status_code
        # self.status = Soup.Status(self.status_code).value_name
        data = message.props.response_body_data.get_data().decode('utf-8')
        data = json.loads(data)
        self.message = data['message']
        self.error_code = data['errorCode']
        self.error_message = data['errorString']

    def __str__(self):
        return '{} ({}): {}'.format(self.error_message, self.error_code, self.message)


class Method(enum.Enum):
    POST = 'POST'
    HEAD = 'HEAD'
    GET = 'GET'


class Message:
    def __init__(self, message: Soup.Message):
        self._message = message

    @classmethod
    def new_for_uri(cls, method: Method, uri: str):
        message = Soup.Message.new(method.value, uri)
        return cls(message)

    @property
    def headers(self) -> Dict[str, str]:
        headers = self._message.props.response_headers
        s = set()
        headers.foreach(lambda k, v: s.add(k))
        return {k: headers.get_list(k) for k in s}

    @headers.setter
    def headers(self, headers: Dict[str, str]):
        h = self._message.props.request_headers
        h.clear()
        for k, v in headers.items():
            h.append(k, v)

    @property
    def json_body(self) -> dict:
        data = self._message.props.response_body_data.get_data()
        return json.loads(data.decode('utf-8')) if data else ''

    @json_body.setter
    def json_body(self, body: dict):
        self._message.set_request('application/json;charset=utf-8',
                                  Soup.MemoryUse.COPY,
                                  json.dumps(body).encode('utf-8'))

    def __str__(self):
        jb = self.json_body
        body = '\n' + json.dumps(jb, indent=3) if jb else ''
        headers = self.headers
        header = json.dumps(headers, indent=3) if headers else ''
        uri = self._message.props.uri.to_string(False)
        return '{}\n{}{}'.format(uri, header, body)


class Session:
    def __init__(self):
        self._session = Soup.Session()
        self._cookies = Soup.CookieJar()
        self._session.add_feature(self._cookies)

    def send_message(self, message: Message) -> Awaitable[Message]:
        future = asyncio.Future()

        def on_response(session, response_message, user_data):
            if response_message.status_code != 200:
                future.set_exception(SoupException(response_message))
            else:
                future.set_result(Message(response_message))

        self._session.queue_message(message._message, on_response, future)
        return future

    def save_cookies_from_response(self, response: Message, origin: str) -> None:
        cookies = response.headers.get('Set-Cookie', '')
        # FIXME: libsoup bindings should accept None for uri
        cookie = Soup.Cookie.parse(cookies, Soup.URI.new(origin))
        if cookie is None:
            raise Exception('Failed to save cookies')

        self._cookies.add_cookie(cookie)

    @property
    def cookies(self) -> Dict[str, str]:
        return {c.get_name(): c.get_value() for c in self._cookies.all_cookies()}
