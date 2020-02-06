import asyncio
import aiohttp


def take_sample(probe_url, specs):
    loop = asyncio.get_event_loop()
    with aiohttp.ClientSession() as session:
        coros = [probe(session, g, spec) for g, spec in specs]
        results = loop.run_until_complete(asyncio.gather(*coros))


async def probe(session, g, spec):
    async with session.post() as response:
        result = await response.json()
        return process_result(g, result)


def process_result(g, result):
    pass
