import pytest

# from conftest import skip_openai
import autogen

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union
from collections import defaultdict


import chess
import chess.svg


# @pytest.mark.skipif(skip_openai, reason="requested to skip openai tests")
def test_nested():
    import autogen

    config_list = autogen.config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    llm_config = {"config_list": config_list}

    financial_tasks = [
        """On which days in 2024 was Microsoft Stock higher than $370? Put results in a table and don't use ``` ``` to include table.""",
        """Investigate the possible reasons of the stock performance.""",
    ]

    assistant = autogen.AssistantAgent(
        "Inner-assistant",
        llm_config=llm_config,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    )

    code_interpreter = autogen.UserProxyAgent(
        "Inner-code-interpreter",
        human_input_mode="NEVER",
        code_execution_config={
            "work_dir": "coding",
            "use_docker": False,
        },
        default_auto_reply="",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    )

    groupchat = autogen.GroupChat(
        agents=[assistant, code_interpreter],
        messages=[],
        speaker_selection_method="round_robin",  # With two agents, this is equivalent to a 1:1 conversation.
        allow_repeat_speaker=False,
        max_round=8,
    )

    manager = autogen.GroupChatManager(
        groupchat=groupchat,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        llm_config=llm_config,
        code_execution_config={
            "work_dir": "coding",
            "use_docker": False,
        },
    )

    financial_assistant_1 = autogen.AssistantAgent(
        name="Financial_assistant_1",
        llm_config={"config_list": config_list},
        # is_termination_msg=lambda x: x.get("content", "") == "",
    )

    user = autogen.UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "tasks",
            "use_docker": False,
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )

    financial_assistant_1.register_nested_chats(
        [autogen.Agent, None], [{"recipient": manager, "summary_method": "reflection_with_llm"}]
    )
    user.initiate_chat(financial_assistant_1, message=financial_tasks[0])


# @pytest.mark.skipif(skip_openai, reason="requested to skip openai tests")
def test_nested_chess():
    config_list_gpt4 = autogen.config_list_from_json(
        "OAI_CONFIG_LIST",
    )
    autogen.config_list_from_json(
        "OAI_CONFIG_LIST",
        filter_dict={"model": "gpt-35-turbo-1106"},
    )

    max_turn = 20

    sys_msg_tmpl = """Your name is {name} and you are a chess player.
    You are playing against {opponent_name}.
    You are playing as {color}.
    You communicate your move using universal chess interface language.
    You also chit-chat with your opponent when you communicate a move to light up the mood.
    You should ensure both you and the opponent are making legal moves.
    Do not apologize for making illegal moves."""

    board_sysm_msg = """You are an AI-powered chess board agent.
    You translate the user's natural language input into legal UCI moves. Note that the user's input may contain the
    UCI move itself, or it may contain a natural language description of the move.
    You should only reply with a UCI move string extracted from the user's input."""

    color_white = "white"
    color_black = "black"
    white_player_name = "PlayerWhite"
    black_player_name = "PlayerBlack"

    class BoardAgent(autogen.AssistantAgent):
        board: chess.Board = chess.Board()
        correct_move_messages: Dict[autogen.Agent, List[Dict]] = defaultdict(list)
        _reply_num: int = 0

        def set_correct_move_messages(self, sender, message, uci_move):
            self.correct_move_messages[sender].extend([message, self._message_to_dict(uci_move)])

        def update_reply_num(self):
            self._reply_num += 1

        @property
        def reply_num(self):
            return self._reply_num

    board_agent = BoardAgent(
        name="BoardAgent",
        system_message=board_sysm_msg,
        llm_config={"temperature": 0.0, "config_list": config_list_gpt4},
        # llm_config={"config_list": config_list_gpt4},
        max_consecutive_auto_reply=max_turn,
    )

    player_white = autogen.AssistantAgent(
        white_player_name,
        system_message=sys_msg_tmpl.format(
            name=white_player_name,
            opponent_name=black_player_name,
            color=color_white,
        ),
        llm_config={"config_list": config_list_gpt4},
        max_consecutive_auto_reply=max_turn,
    )

    player_black = autogen.AssistantAgent(
        black_player_name,
        system_message=sys_msg_tmpl.format(
            name=black_player_name,
            opponent_name=white_player_name,
            color=color_black,
        ),
        # llm_config={"temperature":1, "cache_seed": 1, "config_list": config_list_gpt35},
        llm_config={"config_list": config_list_gpt4},
        # llm_config={"temperature":1, "cache_seed": 1, "config_list": config_list_gpt4},
        max_consecutive_auto_reply=max_turn,
    )

    def player2board_reply(recipient, messages, sender, config):
        board = config if config else ""
        # add a system message about the current state of the board.
        board = sender.board
        board_state_msg = [{"role": "system", "content": f"Current board:\n{board}"}]
        last_message = messages[-1]
        if last_message["content"].startswith("Error"):
            # try again
            _, rep = recipient.generate_oai_reply(messages + board_state_msg, sender)
            # rep = recipient.generate_reply(messages + board_state_msg, sender)
            return True, rep
        else:
            return True, None

    def board_chat_func(chat_queue, recipient, messages, sender, config):
        # TODO: better way to handle this
        if chat_queue[0]["recipient"].reply_num >= max_turn:
            return True, None
        c = chat_queue[0]  # board = config
        board = c["recipient"].board
        board_state_msg = [{"role": "system", "content": f"Current board:\n{board}"}]
        useful_msg = messages[-1].copy()
        useful_msg["content"] = useful_msg.get("content", "") + f"The current board is:\n {board} ."
        oai_messages = [messages[-1]]
        # _, message = recipient.generate_oai_reply(messages + board_state_msg, sender)
        _, message = recipient.generate_oai_reply(oai_messages + board_state_msg, sender)
        c["message"] = message
        # c["carryover"] = f"Current board:\n{board}"  # NOTE: in the old code, this is added as system message
        chat_queue[0] = c
        # print("nessss")
        res = recipient.initiate_chats(chat_queue)
        last_res = list(res.values())[-1]
        # return True, message + "My Move is:\n" + last_res.summary
        return True, last_res.summary

    def board_reply(recipient, messages, sender, config):
        # print("resplyssss")
        if recipient.reply_num >= max_turn:
            return True, None
        org_msg = messages[-1].copy()
        message = messages[-1]
        # extract a UCI move from player's message
        # TODO: better way to handle this
        message["content"] = "Extract a UCI move from the following message \n." + message.get("content", "")
        _, reply = recipient.generate_oai_reply([message], sender)
        # reply = recipient.generate_reply(recipient.correct_move_messages[sender] + [message], sender)
        uci_move = reply if isinstance(reply, str) else str(reply["content"])
        recipient.update_reply_num()
        try:
            recipient.board.push_uci(uci_move)
        except ValueError as e:
            # invalid move
            return True, f"Error: {e}"
        else:
            # valid move
            m = chess.Move.from_uci(uci_move)
            try:
                display(  # noqa: F821
                    chess.svg.board(
                        recipient.board, arrows=[(m.from_square, m.to_square)], fill={m.from_square: "gray"}, size=200
                    )
                )
            except NameError as e:
                print(f"Error displaying board: {e}")
            # better way to handle this
            recipient.set_correct_move_messages(sender, message, uci_move)
            recipient.correct_move_messages[sender][-1]["role"] = "assistant"
            return True, org_msg.get("content", "")  # + "\n Move:" + uci_move

    board_agent.register_reply([white_player_name, black_player_name], board_reply, 0)
    player_white.register_nested_chats(
        black_player_name,
        [{"recipient": board_agent, "summary_method": "last_msg"}],
        board_chat_func,
    )
    player_black.register_nested_chats(
        white_player_name,
        [{"recipient": board_agent, "summary_method": "last_msg"}],
        board_chat_func,
    )
    player_white.register_reply(BoardAgent, player2board_reply)
    player_black.register_reply(BoardAgent, player2board_reply)
    player_white.initiate_chat(player_black, message="Your turn.")


if __name__ == "__main__":
    # test_nested()
    test_nested_chess()
