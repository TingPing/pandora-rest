import asyncio
import json
import secrets
import gi

gi.require_versions({
    'Soup': '2.4',
})

from gi.repository import ( 
    Soup,
)

_session = Soup.Session()


def _soup_headers_to_string(headers: Soup.MessageHeaders):
    l = []; headers.foreach(lambda k, v: l.append((k, v)))
    return '\n'.join('{}: {}'.format(*i) for i in l)


def _print_soup_response(message: Soup.Message):
    print(f'''===========
{message.props.status_code} {Soup.Status(message.props.status_code).value_name}

{_soup_headers_to_string(message.props.response_headers)}

{json.dumps(json.loads(message.props.response_body_data.get_data().decode('utf-8')), indent=3) if message.props.response_body_data.get_data() else 'No data'}
===========
''')


def _print_soup_request(message: Soup.Message):
    print(f'''===========
{message.props.uri.to_string(False)} {message.props.method}

{_soup_headers_to_string(message.props.request_headers)}

{json.dumps(json.loads(message.props.request_body_data.get_data().decode('utf-8')), indent=3)}
===========
''')


def _send_message(method: str, body: dict, csrf_token: str, auth_token: str):
    uri = 'https://www.pandora.com/api/v1/' + method
    message = Soup.Message.new('POST', uri)
    headers = message.props.request_headers
    headers.append('X-CsrfToken', csrf_token)
    headers.append('X-AuthToken', auth_token)
    message.set_request('application/json;charset=utf-8', Soup.MemoryUse.COPY,
                        json.dumps(body).encode('utf-8'))
    _print_soup_request(message)

    future = asyncio.Future()

    def on_response(session, response_message):
        # TODO: Might not have data
        _print_soup_response(response_message)
        data = json.loads(response_message.props.response_body_data.get_data().decode('utf-8'))
        if response_message.status_code != 200:
            future.set_exception(Exception(data['message']))
        else:
            future.set_result(data)

    _session.queue_message(message, on_response)
    return future


def _get_csrf_token():
    message = Soup.Message.new('HEAD', 'https://www.pandora.com')
    future = asyncio.Future()
    
    def on_response(session, response_message):
        _print_soup_response(response_message)
        if response_message.status_code == 200:
            headers = response_message.response_headers
            cookies = headers.get_list('Set-Cookie')
            if cookies is not None:
                cookies = cookies.split(',')
                print(cookies)
                for cookie in cookies:
                    cookie = cookie.lstrip()
                    if cookie.startswith('csrftoken='):
                        token = cookie[len('csrftoken='):].split(';', 1)[0]
                        future.set_result(token)
                        return
        future.set_exception(Exception('Failed to get CSRF token'))

    _session.queue_message(message, on_response)
    return future


class Client:
    def __init__(self):
        self._auth_token = ''
        self._csrf_token = ''

    async def login(self, email: str, password: str):
        self._csrf_token = await _get_csrf_token()
        # TODO: Set token in cookies

        return await _send_message('auth/login', {
            'username': email,
            'password': password,
        }, self._csrf_token, self._auth_token)
