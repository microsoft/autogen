"""This is an example of simulating a chess game with two agents
that play against each other, using tools to reason about the game state
and make moves, and using a group chat manager to orchestrate the conversation."""

import argparse
import asyncio
import logging
from typing import Annotated, Literal

from autogen_core import (
    AgentId,
    AgentInstantiationContext,
    AgentRuntime,
    DefaultSubscription,
    DefaultTopicId,
    SingleThreadedAgentRuntime,
)
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import SystemMessage
from autogen_core.tools import FunctionTool
from chess import BLACK, SQUARE_NAMES, WHITE, Board, Move
from chess import piece_name as get_piece_name
from common.agents._chat_completion_agent import ChatCompletionAgent
from common.patterns._group_chat_manager import GroupChatManager
from common.types import TextMessage
from common.utils import get_chat_completion_client_from_envs


def validate_turn(board: Board, player: Literal["white", "black"]) -> None:
    """Validate that it is the player's turn to move."""
    last_move = board.peek() if board.move_stack else None
    if last_move is not None:
        if player == "white" and board.color_at(last_move.to_square) == WHITE:
            raise ValueError("It is not your turn to move. Wait for black to move.")
        if player == "black" and board.color_at(last_move.to_square) == BLACK:
            raise ValueError("It is not your turn to move. Wait for white to move.")
    elif last_move is None and player != "white":
        raise ValueError("It is not your turn to move. Wait for white to move first.")


def get_legal_moves(
    board: Board, player: Literal["white", "black"]
) -> Annotated[str, "A list of legal moves in UCI format."]:
    """Get legal moves for the given player."""
    validate_turn(board, player)
    legal_moves = list(board.legal_moves)
    if player == "black":
        legal_moves = [move for move in legal_moves if board.color_at(move.from_square) == BLACK]
    elif player == "white":
        legal_moves = [move for move in legal_moves if board.color_at(move.from_square) == WHITE]
    else:
        raise ValueError("Invalid player, must be either 'black' or 'white'.")
    if not legal_moves:
        return "No legal moves. The game is over."

    return "Possible moves are: " + ", ".join([move.uci() for move in legal_moves])


def get_board(board: Board) -> str:
    """Get the current board state."""
    return str(board)


def make_move(
    board: Board,
    player: Literal["white", "black"],
    thinking: Annotated[str, "Thinking for the move."],
    move: Annotated[str, "A move in UCI format."],
) -> Annotated[str, "Result of the move."]:
    """Make a move on the board."""
    validate_turn(board, player)
    new_move = Move.from_uci(move)
    board.push(new_move)

    # Print the move.
    print("-" * 50)
    print("Player:", player)
    print("Move:", new_move.uci())
    print("Thinking:", thinking)
    print("Board:")
    print(board.unicode(borders=True))

    # Get the piece name.
    piece = board.piece_at(new_move.to_square)
    assert piece is not None
    piece_symbol = piece.unicode_symbol()
    piece_name = get_piece_name(piece.piece_type)
    if piece_symbol.isupper():
        piece_name = piece_name.capitalize()
    return f"Moved {piece_name} ({piece_symbol}) from {SQUARE_NAMES[new_move.from_square]} to {SQUARE_NAMES[new_move.to_square]}."


async def chess_game(runtime: AgentRuntime) -> None:  # type: ignore
    """Create agents for a chess game and return the group chat."""

    # Create the board.
    board = Board()

    # Create tools for each player.
    # @functools.wraps(get_legal_moves)
    def get_legal_moves_black() -> str:
        return get_legal_moves(board, "black")

    # @functools.wraps(get_legal_moves)
    def get_legal_moves_white() -> str:
        return get_legal_moves(board, "white")

    # @functools.wraps(make_move)
    def make_move_black(
        thinking: Annotated[str, "Thinking for the move"],
        move: Annotated[str, "A move in UCI format"],
    ) -> str:
        return make_move(board, "black", thinking, move)

    # @functools.wraps(make_move)
    def make_move_white(
        thinking: Annotated[str, "Thinking for the move"],
        move: Annotated[str, "A move in UCI format"],
    ) -> str:
        return make_move(board, "white", thinking, move)

    def get_board_text() -> Annotated[str, "The current board state"]:
        return get_board(board)

    black_tools = [
        FunctionTool(
            get_legal_moves_black,
            name="get_legal_moves",
            description="Get legal moves.",
        ),
        FunctionTool(
            make_move_black,
            name="make_move",
            description="Make a move.",
        ),
        FunctionTool(
            get_board_text,
            name="get_board",
            description="Get the current board state.",
        ),
    ]

    white_tools = [
        FunctionTool(
            get_legal_moves_white,
            name="get_legal_moves",
            description="Get legal moves.",
        ),
        FunctionTool(
            make_move_white,
            name="make_move",
            description="Make a move.",
        ),
        FunctionTool(
            get_board_text,
            name="get_board",
            description="Get the current board state.",
        ),
    ]

    await ChatCompletionAgent.register(
        runtime,
        "PlayerBlack",
        lambda: ChatCompletionAgent(
            description="Player playing black.",
            system_messages=[
                SystemMessage(
                    content="You are a chess player and you play as black. "
                    "Use get_legal_moves() to get list of legal moves. "
                    "Use get_board() to get the current board state. "
                    "Think about your strategy and call make_move(thinking, move) to make a move."
                ),
            ],
            model_context=BufferedChatCompletionContext(buffer_size=10),
            model_client=get_chat_completion_client_from_envs(model="gpt-4o"),
            tools=black_tools,
        ),
    )
    await runtime.add_subscription(DefaultSubscription(agent_type="PlayerBlack"))

    await ChatCompletionAgent.register(
        runtime,
        "PlayerWhite",
        lambda: ChatCompletionAgent(
            description="Player playing white.",
            system_messages=[
                SystemMessage(
                    content="You are a chess player and you play as white. "
                    "Use get_legal_moves() to get list of legal moves. "
                    "Use get_board() to get the current board state. "
                    "Think about your strategy and call make_move(thinking, move) to make a move."
                ),
            ],
            model_context=BufferedChatCompletionContext(buffer_size=10),
            model_client=get_chat_completion_client_from_envs(model="gpt-4o"),
            tools=white_tools,
        ),
    )
    await runtime.add_subscription(DefaultSubscription(agent_type="PlayerWhite"))

    # Create a group chat manager for the chess game to orchestrate a turn-based
    # conversation between the two agents.
    await GroupChatManager.register(
        runtime,
        "ChessGame",
        lambda: GroupChatManager(
            description="A chess game between two agents.",
            model_context=BufferedChatCompletionContext(buffer_size=10),
            participants=[
                AgentId("PlayerWhite", AgentInstantiationContext.current_agent_id().key),
                AgentId("PlayerBlack", AgentInstantiationContext.current_agent_id().key),
            ],  # white goes first
        ),
    )
    await runtime.add_subscription(DefaultSubscription(agent_type="ChessGame"))


async def main() -> None:
    """Main Entrypoint."""
    runtime = SingleThreadedAgentRuntime()
    await chess_game(runtime)
    runtime.start()
    # Publish an initial message to trigger the group chat manager to start
    # orchestration.
    await runtime.publish_message(
        TextMessage(content="Game started.", source="System"),
        topic_id=DefaultTopicId(),
    )
    await runtime.stop_when_idle()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a chess game between two agents.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        handler = logging.FileHandler("chess_game.log")
        logging.getLogger("autogen_core").addHandler(handler)

    asyncio.run(main())
