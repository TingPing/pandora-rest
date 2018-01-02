"""
Provides slightly more pythonic bindings to libsoup

The exact behavior is largely tailored to usage within Pithos.
"""

__license__ = 'GPL-3.0+'

import asyncio
import enum
import gi
gi.require_version('Soup', '2.4')
from gi.repository import GObject, Gio, Soup
import json
from typing import Awaitable, Dict
from soupy_status import SoupyStatus

SUPPORTED_PROXY_PROTOCOLS = (
    'socks://',
    'socks4://',
    'socks5://',
    'http://',
    'https://',
)


class SoupException(Exception):
    def __init__(self, message, error_code, error_message) -> None:
        self.message = message
        self.error_code = error_code
        self.error_message = error_message

    @classmethod
    def new_from_message(cls, soup_message: Soup.Message, status_name: str):
        data = soup_message.props.response_body_data.get_data()
        error_message = []
        if data:
            data = json.loads(data.decode('utf-8'))
            message = data['message']
            error_message.append(data['errorString'])
        else:
            message = 'HTTP Error'
        error_message.append(status_name)
        error_message = '; '.join(error_message)
        return cls(message, soup_message.props.status_code, error_message)

    def __str__(self) -> str:
        return '{} ({}): {}'.format(self.error_message, self.error_code, self.message)


class Message(GObject.Object):
    __gtype_name__ = 'Message'
    def __init__(self, message: Soup.Message, request: bool=False) -> None:
        super().__init__()
        self._message = message
        self._request = request

    @classmethod
    def new_for_uri(cls, method: str, uri: str):
        message = Soup.Message.new(method, uri)
        return cls(message, request=True)

    @GObject.Property(
        type=GObject.TYPE_PYOBJECT,
        nick='headers prop',
        blurb='The message request headers',
        flags=GObject.ParamFlags.READWRITE,
    )
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
        self.notify('headers')

    @GObject.Property(
        type=GObject.TYPE_PYOBJECT,
        nick='json-body prop',
        blurb='The decoded message body',
        flags=GObject.ParamFlags.READWRITE,
    )
    def json_body(self) -> dict:
        data = self.body
        return json.loads(data.decode('utf-8')) if data else ''

    @json_body.setter
    def json_body(self, json_body: dict):
        assert self._request is True
        self._message.set_request('application/json;charset=utf-8',
                                  Soup.MemoryUse.COPY,
                                  json.dumps(json_body).encode('utf-8'))
        self.notify('body')
        self.notify('json-body')

    @GObject.Property(
        type=GObject.TYPE_PYOBJECT,
        nick='body prop',
        blurb='un-encoded bytes from response',
        flags=GObject.ParamFlags.READABLE,
    )
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

class Session(GObject.Object):
    __gtype_name__ = 'Session'
    def __init__(self):
        super().__init__()
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
            try:
                status = SoupyStatus(response_message.status_code)
            except (TypeError, ValueError):
                status = SoupyStatus.UNKNOWN_STATUS_CODE 
            if status is not SoupyStatus.OK:
                future.set_exception(SoupException.new_from_message(response_message, status.name))
            else:
                future.set_result(Message(response_message))

        self._session.queue_message(message._message, on_response)
        return future

    @GObject.Property(
        type=str,
        default='',
        nick='proxy prop',
        blurb='Proxy to be used by the session',
        flags=GObject.ParamFlags.READWRITE,
    )
    def proxy(self) -> str:
        """Proxy to be used by the session.

        SOCKS (4/5) and HTTP are currently supported.

        An empty string means disabled (respect system default).
        """
        uri = self._session.props.proxy_uri
        return uri.to_string(False) if uri else ''

    @GObject.Property(
        type=GObject.TYPE_PYOBJECT,
        nick='parsed-proxy prop',
        blurb='Proxy to be used by the session, parsed',
        flags=GObject.ParamFlags.READABLE,
    )
    def parsed_proxy(self) -> dict:
        proxy = {}
        uri = self._session.props.proxy_uri
        if uri:
            proxy['scheme'] = uri.get_scheme()
            proxy['user'] = uri.get_user()
            proxy['password'] = uri.get_password()
            proxy['hostport'] = uri.get_port()
        return proxy

    @proxy.setter
    def proxy(self, proxy: str) -> None:
        if not proxy:
            # Return to default state
            self._session.props.proxy_resolver = Gio.ProxyResolver.get_default()
        else:
            if not proxy.startswith(SUPPORTED_PROXY_PROTOCOLS):
                raise SoupException('Invalid proxy URI', -1, '')
            self._session.props.proxy_uri = Soup.URI.new(proxy)
        self.notify('proxy')
        self.notify('parsed-proxy')

    def _save_cookies_from_response(self, response: Message, origin: str) -> None:
        cookies = response.headers.get('Set-Cookie', '')
        # FIXME: libsoup bindings should accept None for uri
        cookie = Soup.Cookie.parse(cookies, Soup.URI.new(origin))
        if cookie is not None:
            self._cookies.add_cookie(cookie)
            self.notify('cookies')

    @GObject.Property(
        type=GObject.TYPE_PYOBJECT,
        nick='cookies prop',
        blurb='Cookies saved in the session',
        flags=GObject.ParamFlags.READABLE,
    )
    def cookies(self) -> Dict[str, str]:
        """Cookies saved in the session"""
        return {c.get_name(): c.get_value() for c in self._cookies.all_cookies()}
