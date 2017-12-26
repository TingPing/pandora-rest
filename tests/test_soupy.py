import pytest
import soupy


@pytest.mark.asyncio
async def test_session():
    session = soupy.Session()

    ret = await session.get('https://httpbin.org/get')
    assert ret.headers['Content-Type'] == 'application/json'
    assert ret.json_body['url'] == 'https://httpbin.org/get'

    body = {'key': 'val'}
    ret = await session.post('https://httpbin.org/post', body)
    assert ret.json_body['json'] == body
