import argparse
import asyncio
import yaml
import random

import chess
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import ChatCompletionClient


def create_ai_player() -> AssistantAgent:
    # Load the model client from config.
    with open("model_config.yaml", "r") as f:
        model_config = yaml.safe_load(f)
    model_client = ChatCompletionClient.load_component(model_config)
    # Create an agent that can use the model client.
    player = AssistantAgent(
        name="ai_player",
        model_client=model_client,
        system_message=None,
        model_client_stream=True,  # Enable streaming for the model client.
        model_context=BufferedChatCompletionContext(buffer_size=10),  # Model context limited to the last 10 messages.
    )
    return player


def get_random_move(board: chess.Board) -> str:
    legal_moves = list(board.legal_moves)
    move = random.choice(legal_moves)
    return move.uci()


def get_ai_prompt(board: chess.Board) -> str:
    try:
        last_move = board.peek().uci()
    except IndexError:
        last_move = None
    # Current player color.
    player_color = "white" if board.turn == chess.WHITE else "black"
    user_color = "black" if player_color == "white" else "white"
    legal_moves = ", ".join([move.uci() for move in board.legal_moves])
    if last_move is None:
        prompt = f"New Game!\nBoard: {board.fen()}\nYou play {player_color}\nYour legal moves: {legal_moves}\n"
    else:
        prompt = f"Board: {board.fen()}\nYou play {player_color}\nUser ({user_color})'s last move: {last_move}\nYour legal moves: {legal_moves}\n"
    example_move = get_random_move(board)
    return (
        prompt
        + "Respond with this format: <move>{your move in UCI format}</move>. "
        + f"For example, <move>{example_move}</move>."
    )


def get_user_prompt(board: chess.Board) -> str:
    try:
        last_move = board.peek().uci()
    except IndexError:
        last_move = None
    # Current player color.
    player_color = "white" if board.turn == chess.WHITE else "black"
    legal_moves = ", ".join([move.uci() for move in board.legal_moves])
    board_display = board.unicode(borders=True)
    if last_move is None:
        prompt = f"New Game!\nBoard:\n{board_display}\nYou play {player_color}\nYour legal moves: {legal_moves}\n"
    prompt = f"Board:\n{board_display}\nYou play {player_color}\nAI's last move: {last_move}\nYour legal moves: {legal_moves}\n"
    return prompt + "Enter your move in UCI format: "


def extract_move(response: str) -> str:
    start = response.find("<move>") + len("<move>")
    end = response.find("</move>")
    if start == -1 or end == -1:
        raise ValueError("Invalid response format.")
    return response[start:end]


async def get_ai_move(board: chess.Board, player: AssistantAgent, max_tries: int) -> str:
    task = get_ai_prompt(board)
    count = 0
    while count < max_tries:
        result = await Console(player.run_stream(task=task))
        count += 1
        response = result.messages[-1].content
        assert isinstance(response, str)
        # Check if the response is a valid UC move.
        try:
            move = chess.Move.from_uci(extract_move(response))
        except (ValueError, IndexError):
            task = "Invalid format. Please read instruction.\n" + get_ai_prompt(board)
            continue
        # Check if the move is legal.
        if move not in board.legal_moves:
            task = "Invalid move. Please enter a move from the list of legal moves.\n" + get_ai_prompt(board)
            continue
        return move.uci()
    # If the player does not provide a valid move, return a random move.
    return get_random_move(board)


async def main(human_player: bool, max_tries: int) -> None:
    board = chess.Board()
    player = create_ai_player()
    while not board.is_game_over():
        # Get the AI's move.
        ai_move = await get_ai_move(board, player, max_tries)
        # Make the AI's move.
        board.push(chess.Move.from_uci(ai_move))
        # Check if the game is over.
        if board.is_game_over():
            break
        # Get the user's move.
        if human_player:
            user_move = input(get_user_prompt(board))
        else:
            user_move = get_random_move(board)
        # Make the user's move.
        board.push(chess.Move.from_uci(user_move))
        print("--------- User --------")
        print(user_move)
        print("-------- Board --------")
        print(board.unicode(borders=True))

    result = "AI wins!" if board.result() == "1-0" else "User wins!" if board.result() == "0-1" else "Draw!"
    print("----------------")
    print(f"Game over! Result: {result}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--human", action="store_true", help="Enable human vs. AI mode.")
    parser.add_argument(
        "--max-tries", type=int, default=10, help="Maximum number of tries for AI input before a random move take over."
    )
    args = parser.parse_args()
    asyncio.run(main(args.human, args.max_tries))
