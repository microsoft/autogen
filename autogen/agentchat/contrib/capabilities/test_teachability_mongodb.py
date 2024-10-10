from turtle import dot
import dotenv

dotenv.load_dotenv()
from debugpy import connect
from teachability_mongodb import (
    Teachability_MongoDBvCore,
)
from autogen_llm_config import llm_config
import os
from autogen.agentchat.conversable_agent import ConversableAgent


def test___init__():
    teachability = Teachability_MongoDBvCore(
        connection_string=os.getenv("MONGODB_CONNECTION_STRING"),
        mongodb_database_name="memos",
        mongodb_collection_name="memo_pairs",
    )
    assert teachability is not None


def test_add_to_agent():
    # create autogen agent
    from autogen.agentchat.conversable_agent import ConversableAgent

    agent = ConversableAgent("test_agent", llm_config=llm_config)
    # create teachability
    teachability = Teachability_MongoDBvCore(
        connection_string=os.getenv("MONGODB_CONNECTION_STRING"),
        mongodb_database_name="memos",
        mongodb_collection_name="memo_pairs",
    )
    # add teachability to agent
    teachability.add_to_agent(agent)
    assert agent.system_message.endswith("conversations.")


def test_prepopulate_db():
    teachability = Teachability_MongoDBvCore(
        connection_string=os.getenv("MONGODB_CONNECTION_STRING"),
        mongodb_database_name="memos",
        mongodb_collection_name="memo_pairs",
    )
    # teachability.prepopulate_db()
    pass


def test_process_last_received_message():
    teachability = Teachability_MongoDBvCore(
        connection_string=os.getenv("MONGODB_CONNECTION_STRING"),
        mongodb_database_name="memos",
        mongodb_collection_name="memo_pairs",
    )
    agent = ConversableAgent("test_agent", llm_config=llm_config)
    teachability.add_to_agent(agent)
    expanded_text = teachability.process_last_received_message(
        "Hello this is a message to process"
    )
    assert expanded_text is not None


def test_consider_memo_storage():
    teachability = Teachability_MongoDBvCore(
        connection_string=os.getenv("MONGODB_CONNECTION_STRING"),
        mongodb_database_name="memos",
        mongodb_collection_name="memo_pairs",
    )
    # teachability.consider_memo_storage()
    # assert teachability.memo_storage is not None
    pass


def test_consider_memo_retrieval():
    teachability = Teachability_MongoDBvCore(
        connection_string=os.getenv("MONGODB_CONNECTION_STRING"),
        mongodb_database_name="memos",
        mongodb_collection_name="memo_pairs",
    )
    agent = ConversableAgent("test_agent", llm_config=llm_config)
    teachability.add_to_agent(agent)
    memo_list = teachability._consider_memo_retrieval("This is a memo.")
    assert memo_list is not None


def test_retrieve_relevant_memos():
    teachability = Teachability_MongoDBvCore(
        connection_string=os.getenv("MONGODB_CONNECTION_STRING"),
        mongodb_database_name="memos",
        mongodb_collection_name="memo_pairs",
    )
    memo_list = teachability._retrieve_relevant_memos("This is a memo.")
    assert memo_list is not None


def test_concatenate_memo_texts():
    teachability = Teachability_MongoDBvCore(
        connection_string=os.getenv("MONGODB_CONNECTION_STRING"),
        mongodb_database_name="memos",
        mongodb_collection_name="memo_pairs",
    )
    memo_list = ["hello", "there"]
    memo_text = teachability._concatenate_memo_texts(memo_list)
    assert memo_text is not None


def test_analyze():
    teachability = Teachability_MongoDBvCore(
        connection_string=os.getenv("MONGODB_CONNECTION_STRING"),
        mongodb_database_name="memos",
        mongodb_collection_name="memo_pairs",
    )
    agent = ConversableAgent("test_agent", llm_config=llm_config)
    teachability.add_to_agent(agent)
    last_message = teachability._analyze("This is a memo.", "Please analyze this memo.")
    assert last_message is not None


def test_mongodbvcore__init__():
    from teachability_mongodb import MongoDBvCoreMemoStore

    mongodbvcorememostore = MongoDBvCoreMemoStore(
        connection_string=os.getenv("MONGODB_CONNECTION_STRING"),
        mongodb_database_name="memos",
        mongodb_collection_name="memo_pairs",
    )
    assert mongodbvcorememostore is not None


def test_create_vector_index_if_not_exists():
    from teachability_mongodb import MongoDBvCoreMemoStore

    mongodbvcorememostore = MongoDBvCoreMemoStore(
        connection_string=os.getenv("MONGODB_CONNECTION_STRING"),
        mongodb_database_name="memos",
        mongodb_collection_name="memo_pairs",
    )
    vector_index_is_created = mongodbvcorememostore._create_vector_index_if_not_exists()
    assert mongodbvcorememostore is not None


def test_add_input_output_pair():
    from teachability_mongodb import MongoDBvCoreMemoStore

    mongodbvcorememostore = MongoDBvCoreMemoStore(
        connection_string=os.getenv("MONGODB_CONNECTION_STRING"),
        mongodb_database_name="memos",
        mongodb_collection_name="memo_pairs",
    )

    input_text = "This is a test input."
    output_text = "This is a test output."
    response_from_db = mongodbvcorememostore.add_input_output_pair(
        input_text, output_text
    )
    assert response_from_db is not None
