"""This is an example of simulating a chess game with two agents
that play against each other, using tools to reason about the game state
and make moves.
You must have OPENAI_API_KEY set up in your environment to run this example.
"""

import argparse
import asyncio
import logging
from typing import Annotated

from agnext.application import SingleThreadedAgentRuntime
from agnext.chat.agents.chat_completion_agent import ChatCompletionAgent
from agnext.chat.patterns.group_chat import GroupChat, GroupChatOutput
from agnext.chat.types import TextMessage
from agnext.components.models import OpenAI, SystemMessage
from agnext.components.tools import FunctionTool
from agnext.core import AgentRuntime
from chess import SQUARE_NAMES, Board, Move
from chess import piece_name as get_piece_name

logging.basicConfig(level=logging.WARNING)
logging.getLogger("agnext").setLevel(logging.DEBUG)


class ChessGameOutput(GroupChatOutput):  # type: ignore
    def on_message_received(self, message: TextMessage) -> None:  # type: ignore
        pass

    def get_output(self) -> None:
        pass

    def reset(self) -> None:
        pass


def chess_game(runtime: AgentRuntime) -> GroupChat:  # type: ignore
    """Create agents for a chess game and return the group chat."""

    # Create the board.
    board = Board()

    # Create shared tools.
    def get_legal_moves() -> Annotated[str, "A list of legal moves in UCI format."]:
        return "Possible moves are: " + ", ".join([str(move) for move in board.legal_moves])

    get_legal_moves_tool = FunctionTool(get_legal_moves, description="Get legal moves.")

    def make_move(input: Annotated[str, "A move in UCI format."]) -> Annotated[str, "Result of the move."]:
        move = Move.from_uci(input)
        board.push(move)
        print(board.unicode(borders=True))
        # Get the piece name.
        piece = board.piece_at(move.to_square)
        assert piece is not None
        piece_symbol = piece.unicode_symbol()
        piece_name = get_piece_name(piece.piece_type)
        if piece_symbol.isupper():
            piece_name = piece_name.capitalize()
        return f"Moved {piece_name} ({piece_symbol}) from {SQUARE_NAMES[move.from_square]} to {SQUARE_NAMES[move.to_square]}."

    make_move_tool = FunctionTool(make_move, description="Call this tool to make a move.")

    tools = [get_legal_moves_tool, make_move_tool]

    black = ChatCompletionAgent(
        name="PlayerBlack",
        description="Player playing black.",
        runtime=runtime,
        system_messages=[
            SystemMessage(
                content="You are a chess player and you play as black. "
                "First call get_legal_moves() first, to get list of legal moves. "
                "Then call make_move(move) to make a move."
            ),
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
        tools=tools,
    )
    white = ChatCompletionAgent(
        name="PlayerWhite",
        description="Player playing white.",
        runtime=runtime,
        system_messages=[
            SystemMessage(
                content="You are a chess player and you play as white. "
                "First call get_legal_moves() first, to get list of legal moves. "
                "Then call make_move(move) to make a move."
            ),
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
        tools=tools,
    )
    game_chat = GroupChat(
        name="ChessGame",
        description="A chess game between two agents.",
        runtime=runtime,
        agents=[white, black],
        num_rounds=10,
        output=ChessGameOutput(),
    )
    return game_chat


async def main(message: str) -> None:
    runtime = SingleThreadedAgentRuntime()
    game_chat = chess_game(runtime)
    future = runtime.send_message(TextMessage(content=message, source="Human"), game_chat)
    while not future.done():
        await runtime.process_next()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a chess game between two agents.")
    parser.add_argument(
        "--initial-message",
        default="Please make a move.",
        help="The initial message to send to the agent playing white.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.initial_message))
