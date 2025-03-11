"""This is an example of simulating a chess game with two agents
that play against each other, using tools to reason about the game state
and make moves. The agents subscribe to the default topic and publish their
moves to the default topic."""

import argparse
import asyncio
import logging
import yaml
from typing import Annotated, Any, Dict, List, Literal

from autogen_core import (
    AgentId,
    AgentRuntime,
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    default_subscription,
    message_handler,
)
from autogen_core.model_context import BufferedChatCompletionContext, ChatCompletionContext
from autogen_core.models import (
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tool_agent import ToolAgent, tool_agent_caller_loop
from autogen_core.tools import FunctionTool, Tool, ToolSchema
from chess import BLACK, SQUARE_NAMES, WHITE, Board, Move
from chess import piece_name as get_piece_name
from pydantic import BaseModel


class TextMessage(BaseModel):
    source: str
    content: str


@default_subscription
class PlayerAgent(RoutedAgent):
    def __init__(
        self,
        description: str,
        instructions: str,
        model_client: ChatCompletionClient,
        model_context: ChatCompletionContext,
        tool_schema: List[ToolSchema],
        tool_agent_type: str,
    ) -> None:
        super().__init__(description=description)
        self._system_messages: List[LLMMessage] = [SystemMessage(content=instructions)]
        self._model_client = model_client
        self._tool_schema = tool_schema
        self._tool_agent_id = AgentId(tool_agent_type, self.id.key)
        self._model_context = model_context

    @message_handler
    async def handle_message(self, message: TextMessage, ctx: MessageContext) -> None:
        # Add the user message to the model context.
        await self._model_context.add_message(UserMessage(content=message.content, source=message.source))
        # Run the caller loop to handle tool calls.
        messages = await tool_agent_caller_loop(
            self,
            tool_agent_id=self._tool_agent_id,
            model_client=self._model_client,
            input_messages=self._system_messages + (await self._model_context.get_messages()),
            tool_schema=self._tool_schema,
            cancellation_token=ctx.cancellation_token,
        )
        # Add the assistant message to the model context.
        for msg in messages:
            await self._model_context.add_message(msg)
        # Publish the final response.
        assert isinstance(messages[-1].content, str)
        await self.publish_message(TextMessage(content=messages[-1].content, source=self.id.type), DefaultTopicId())


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


async def chess_game(runtime: AgentRuntime, model_client : ChatCompletionClient) -> None:  # type: ignore
    """Create agents for a chess game and return the group chat."""

    # Create the board.
    board = Board()

    # Create tools for each player.
    def get_legal_moves_black() -> str:
        return get_legal_moves(board, "black")

    def get_legal_moves_white() -> str:
        return get_legal_moves(board, "white")

    def make_move_black(
        thinking: Annotated[str, "Thinking for the move"],
        move: Annotated[str, "A move in UCI format"],
    ) -> str:
        return make_move(board, "black", thinking, move)

    def make_move_white(
        thinking: Annotated[str, "Thinking for the move"],
        move: Annotated[str, "A move in UCI format"],
    ) -> str:
        return make_move(board, "white", thinking, move)

    def get_board_text() -> Annotated[str, "The current board state"]:
        return get_board(board)

    black_tools: List[Tool] = [
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

    white_tools: List[Tool] = [
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

    # Register the agents.
    await ToolAgent.register(
        runtime,
        "PlayerBlackToolAgent",
        lambda: ToolAgent(description="Tool agent for chess game.", tools=black_tools),
    )

    await ToolAgent.register(
        runtime,
        "PlayerWhiteToolAgent",
        lambda: ToolAgent(description="Tool agent for chess game.", tools=white_tools),
    )

    await PlayerAgent.register(
        runtime,
        "PlayerBlack",
        lambda: PlayerAgent(
            description="Player playing black.",
            instructions="You are a chess player and you play as black. Use the tool 'get_board' and 'get_legal_moves' to get the legal moves and 'make_move' to make a move.",
            model_client=model_client,
            model_context=BufferedChatCompletionContext(buffer_size=10),
            tool_schema=[tool.schema for tool in black_tools],
            tool_agent_type="PlayerBlackToolAgent",
        ),
    )

    await PlayerAgent.register(
        runtime,
        "PlayerWhite",
        lambda: PlayerAgent(
            description="Player playing white.",
            instructions="You are a chess player and you play as white. Use the tool 'get_board' and 'get_legal_moves' to get the legal moves and 'make_move' to make a move.",
            model_client=model_client,
            model_context=BufferedChatCompletionContext(buffer_size=10),
            tool_schema=[tool.schema for tool in white_tools],
            tool_agent_type="PlayerWhiteToolAgent",
        ),
    )


async def main(model_config: Dict[str, Any]) -> None:
    """Main Entrypoint."""
    runtime = SingleThreadedAgentRuntime()
    model_client = ChatCompletionClient.load_component(model_config)
    await chess_game(runtime, model_client)
    runtime.start()
    # Publish an initial message to trigger the group chat manager to start
    # orchestration.
    # Send an initial message to player white to start the game.
    await runtime.send_message(
        TextMessage(content="Game started, white player your move.", source="System"),
        AgentId("PlayerWhite", "default"),
    )
    await runtime.stop_when_idle()
    await model_client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a chess game between two agents.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument(
        "--model-config", type=str, help="Path to the model configuration file.", default="model_config.yml"
    )
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        handler = logging.FileHandler("chess_game.log")
        logging.getLogger("autogen_core").addHandler(handler)

    with open(args.model_config, "r") as f:
        model_config = yaml.safe_load(f)
    asyncio.run(main(model_config))
