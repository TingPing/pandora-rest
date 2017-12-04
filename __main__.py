import asyncio
import gbulb
from pandora import Client

gbulb.install()
loop = asyncio.get_event_loop()
client = Client()


async def login():
    print(await client.login('bob@bob.com', 'password'))
    print(await client.get_stations())
    

asyncio.ensure_future(login()).add_done_callback(lambda x: loop.stop())

loop.run_forever()
