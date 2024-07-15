import asyncio
import os

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import Image, TypeRoutedAgent, message_handler
from agnext.core import CancellationToken
from app import build_app
from dotenv import load_dotenv
from messages import ArticleCreated, AuditorAlert, AuditText, GraphicDesignCreated


class Printer(TypeRoutedAgent):
    def __init__(
        self,
    ) -> None:
        super().__init__("")

    @message_handler
    async def handle_graphic_design(self, message: GraphicDesignCreated, cancellation_token: CancellationToken) -> None:
        image = Image.from_uri(message.image_uri)
        # Save image to random name in current directory
        image.image.save(os.path.join(os.getcwd(), f"{message.user_id}.png"))
        print(f"Received GraphicDesignCreated: user {message.user_id}, saved to {message.user_id}.png")

    @message_handler
    async def handle_auditor_alert(self, message: AuditorAlert, cancellation_token: CancellationToken) -> None:
        print(f"Received AuditorAlert: {message.auditor_alert_message} for user {message.user_id}")


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    await build_app(runtime)
    runtime.register("Printer", lambda: Printer())

    ctx = runtime.start()

    await runtime.publish_message(
        AuditText(text="Buy my product for a MASSIVE 50% discount.", user_id="user-1"), namespace="default"
    )

    await runtime.publish_message(
        ArticleCreated(article="The best article ever written about trees and rocks", user_id="user-2"),
        namespace="default",
    )

    await ctx.stop_when_idle()


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
