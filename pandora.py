import soupy


class Client:
    def __init__(self):
        self._session = soupy.Session()
        self._auth_token = ''
        self._csrf_token = ''

    async def _get_csrf_token(self) -> str:
        uri = 'https://www.pandora.com'
        message = soupy.Message.new_for_uri(soupy.Method.HEAD, uri)
        response = await self._session.send_message(message)
        self._session.save_cookies_from_response(response, uri)
        return self._session.cookies['csrftoken']

    async def _send_message(self, method: str, body: str) -> dict:
        uri = 'https://www.pandora.com/api/' + method
        message = soupy.Message.new_for_uri(soupy.Method.POST, uri)
        message.headers = {'X-CsrfToken': self._csrf_token,
                           'X-AuthToken': self._auth_token}
        message.json_body = body

        response = await self._session.send_message(message)
        return response.json_body

    async def login(self, email: str, password: str) -> dict:
        self._csrf_token = await self._get_csrf_token()

        response = await self._send_message('v1/auth/login', {
            'username': email,
            'password': password,
        })
        self._auth_token = response['authToken']
        return response
