"""
Provides slightly more pythonic bindings to libsoup

The exact behavior is largely tailored to usage within Pithos.
"""

__license__ = 'GPL-3.0+'

import asyncio
import enum
import gi
gi.require_version('Soup', '2.4')
from gi.repository import Gio, Soup
import json
from typing import Awaitable, Dict


class SoupException(Exception):
    def __init__(self, message: Soup.Message) -> None:
        # self.status_code = message.props.status_code
        # self.status = Soup.Status(self.status_code).value_name
        data = message.props.response_body_data.get_data().decode('utf-8')
        data = json.loads(data)
        self.message = data['message']
        self.error_code = data['errorCode']
        self.error_message = data['errorString']

    def __str__(self) -> str:
        return '{} ({}): {}'.format(self.error_message, self.error_code, self.message)


class Message:
    def __init__(self, message: Soup.Message, request: bool=False) -> None:
        self._message = message
        self._request = request

    @classmethod
    def new_for_uri(cls, method: str, uri: str):
        message = Soup.Message.new(method, uri)
        return cls(message, request=True)

    @property
    def headers(self) -> Dict[str, str]:
        headers = self._message.props.request_headers if self._request else self._message.props.response_headers
        s = set()
        headers.foreach(lambda k, v: s.add(k))
        return {k: headers.get_list(k) for k in s}

    @headers.setter
    def headers(self, headers: Dict[str, str]):
        assert self._request is True
        h = self._message.props.request_headers
        h.clear()
        for k, v in headers.items():
            h.append(k, v)

    @property
    def json_body(self) -> dict:
        data = self.body
        return json.loads(data.decode('utf-8')) if data else ''

    @json_body.setter
    def json_body(self, json_body: dict):
        assert self._request is True
        self._message.set_request('application/json;charset=utf-8',
                                  Soup.MemoryUse.COPY,
                                  json.dumps(json_body).encode('utf-8'))

    @property
    def body(self) -> bytes:
        """Returns raw un-encoded bytes from response"""
        if self._request is True:
            data = self._message.props.request_body_data
        else:
            data = self._message.props.response_body_data
        return data.get_data()

    def __str__(self):
        jb = self.json_body
        body = '\n' + json.dumps(jb, indent=3) if jb else ''
        headers = self.headers
        header = json.dumps(headers, indent=3) if headers else ''
        uri = self._message.props.uri.to_string(False)
        return '{}\n{}{}'.format(uri, header, body)

    def __repr__(self):
        uri = self._message.props.uri.to_string(False)
        return "<Message '{}': '{}' - '{}'>".format(uri, self.headers, self.body)

class Session:
    def __init__(self):
        self._session = Soup.Session()
        self._cookies = Soup.CookieJar()
        self._session.add_feature(self._cookies)

    async def head(self, uri: str) -> Message:
        """
        Sends HTTP HEAD request. Cookies in response are saved to session

        :param uri: URI to send request to.
        """
        message = Message.new_for_uri('HEAD', uri)
        response = await self._send_message(message)
        self._save_cookies_from_response(response, uri)
        return response

    async def post(self, uri: str, json_body: dict=None, headers: dict=None) -> Message:
        """
        Sends HTTP POST request.

        :param uri: URI to send request to.
        :param json_body: Body to send, converted to JSON encoded in UTF-8.
        :param headers: Headers to send.
        """
        message = Message.new_for_uri('POST', uri)
        if headers is not None:
            message.headers = headers
        if json_body is not None:
            message.json_body = json_body
        return await self._send_message(message)

    async def get(self, uri: str) -> Message:
        """Sends an HTTP GET request.

        :param uri: URI to send request to.
        """
        message = Message.new_for_uri('GET', uri)
        return await self._send_message(message)

    def _send_message(self, message: Message) -> Awaitable[Message]:
        future = asyncio.Future()  # type: asyncio.Future

        def on_response(session, response_message):
            if response_message.status_code != 200:
                future.set_exception(SoupException(response_message))
            else:
                future.set_result(Message(response_message))

        self._session.queue_message(message._message, on_response)
        return future

    @property
    def proxy(self) -> str:
        """Proxy to be used by the session.

        SOCKS (4/5) and HTTP are currently supported.

        An empty string means disabled (respect system default).
        """
        uri = self._session.props.proxy_uri
        return uri.to_string(False) if uri else ''

    @proxy.setter
    def proxy(self, proxy: str) -> None:
        if not proxy:
            # Return to default state
            self._session.props.proxy_resolver = Gio.ProxyResolver.get_default()
        else:
            self._session.props.proxy_uri = Soup.URI.new(proxy)

    def _save_cookies_from_response(self, response: Message, origin: str) -> None:
        cookies = response.headers.get('Set-Cookie', '')
        # FIXME: libsoup bindings should accept None for uri
        cookie = Soup.Cookie.parse(cookies, Soup.URI.new(origin))
        if cookie is not None:
            self._cookies.add_cookie(cookie)

    @property
    def cookies(self) -> Dict[str, str]:
        """Cookies saved in the session"""
        return {c.get_name(): c.get_value() for c in self._cookies.all_cookies()}
