from autogen import AssistantAgent, UserProxyAgent
from autogen import GroupChat, GroupChatManager
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST
import pytest
from conftest import skip_openai
import autogen
from typing import Literal
from typing_extensions import Annotated
from autogen import initiate_chats
from autogen import Chat, Link

from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

import chess
import chess.svg


@pytest.mark.skipif(skip_openai, reason="requested to skip openai tests")
def test_chats_chess():
    autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )

    config_list_gpt4 = autogen.config_list_from_json(
        "OAI_CONFIG_LIST",
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
    You translate the user's natural language input into legal UCI moves.
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
        llm_config={"config_list": config_list_gpt4},
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
        llm_config={"config_list": config_list_gpt4},
        max_consecutive_auto_reply=max_turn,
    )

    def board_response(recipient, messages, sender, config):
        # print("resplyssss")
        if recipient.reply_num >= max_turn:
            return True, None
        org_msg = messages[-1].copy()
        message = messages[-1]
        # extract a UCI move from player's message
        # TODO: better way to handle this
        message["content"] = "Extract a UCI move from the following message \n." + message.get("content", "")
        _, reply = recipient.generate_oai_reply([message], sender)
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
            return sender, org_msg.get("content", "")  # + "\n Move:" + uci_move

    def player_response(recipient, messages, sender, config):
        board = config if config else ""
        # add a system message about the current state of the board.
        board = sender.board
        board_state_msg = [{"role": "system", "content": f"Current board:\n{board}"}]
        last_message = messages[-1]

        if recipient == board:
            if last_message["content"].startswith("Error"):
                _, rep = recipient.generate_oai_reply(messages + board_state_msg, sender)
                return board_agent, rep
            else:
                if recipient == player_white:
                    return player_black, None
                elif recipient == player_black:
                    return player_white, None
        if recipient == player_white:
            _, rep = recipient.generate_oai_reply(messages + board_state_msg, sender)
            return player_black, rep

    player_black.register_response(player_response)
    player_white.register_response(player_response)
    board_agent.register_response(board_response)
    player_white2player_black = autogen.Link(
        player_white,
        player_black,
        init_message="Your turn!",
    )
    player_white2board = autogen.Link(player_white, board_agent)
    player_black2board = autogen.Link(player_black, board_agent)
    conversational_chess = autogen.Chat(links=[player_white2player_black, player_white2board, player_black2board])
    conversational_chess.initiate_chats()


@pytest.mark.skipif(skip_openai, reason="requested to skip openai tests")
def test_chats_class():
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )

    financial_tasks = [
        """What are the full names of NVDA and TESLA.""",
        """Get their stock price.""",
        """Analyze pros and cons. Keep it short.""",
    ]

    writing_tasks = ["""Develop a short but engaging blog post using any information provided."""]

    financial_assistant_1 = AssistantAgent(
        name="Financial_assistant_1",
        llm_config={"config_list": config_list},
    )
    financial_assistant_2 = AssistantAgent(
        name="Financial_assistant_2",
        llm_config={"config_list": config_list},
    )
    writer = AssistantAgent(
        name="Writer",
        llm_config={"config_list": config_list},
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        system_message="""
            You are a professional writer, known for
            your insightful and engaging articles.
            You transform complex concepts into compelling narratives.
            Reply "TERMINATE" in the end when everything is done.
            """,
    )

    user = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "tasks",
            "use_docker": False,
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )

    user_2 = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        max_consecutive_auto_reply=3,
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "tasks",
            "use_docker": False,
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )

    def my_summary_method(recipient, sender):
        return recipient.chat_messages[sender][0].get("content", "")

    research_link_1 = Link(
        sender=user, recipient=financial_assistant_1, init_message=financial_tasks[0], summary_method=my_summary_method
    )
    research_link_2 = Link(
        sender=user_2,
        recipient=financial_assistant_2,
        init_message=financial_tasks[1],
        summary_method="reflection_with_llm",
    )
    writing_link = Link(
        sender=user,
        recipient=writer,
        init_message=writing_tasks[0],
        carryover="I want to include a figure or a table of data in the blogpost.",
        summary_method="last_msg",
    )

    my_chat = Chat()
    chat_res = my_chat.initiate_chats(
        [research_link_1, research_link_2, writing_link], allow_carryover_across_chats=True
    )
    print(chat_res, len(chat_res))
    chat_w_writer = chat_res[-1]
    print(chat_w_writer.chat_history, chat_w_writer.summary, chat_w_writer.cost)

    print(chat_res[0].human_input)
    print(chat_res[0].summary)
    print(chat_res[0].chat_history)
    print(chat_res[1].summary)
    # print(blogpost.summary, insights_and_blogpost)


if __name__ == "__main__":
    # test_chats()
    # test_chats_general()
    # test_chats_exceptions()
    # test_chats_group()
    # test_chats_w_func()
    # test_chat_messages_for_summary()
    test_chats_class()
