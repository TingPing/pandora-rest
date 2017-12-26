import pytest
import soupy


@pytest.mark.asyncio
async def test_session():
    session = soupy.Session()

    ret = await session.get('https://httpbin.org/get')
    assert ret.headers['Content-Type'] == 'application/json'
    assert ret.json_body['url'] == 'https://httpbin.org/get'
