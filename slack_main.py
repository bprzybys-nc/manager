from src.slack_worker import slack_async_integration
from src.config import SLACK_APP_TOKEN

from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler


async def main():
    handler = AsyncSocketModeHandler(slack_async_integration.app, SLACK_APP_TOKEN)
    await handler.start_async()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
