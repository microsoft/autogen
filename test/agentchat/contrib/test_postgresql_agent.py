#!/usr/bin/env python3 -m pytest

import os
import sys

import pytest

from autogen import config_list_from_json

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from conftest import skip_openai  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

from autogen import AssistantAgent
from autogen.coding.markdown_code_extractor import MarkdownCodeExtractor

try:
    import psycopg

    from autogen.agentchat.contrib.postgresql_agent import PostgreSqlAgent, PostgreSqlQueryExecutor
except ImportError:
    skip = True
else:
    skip = False

db_name = "postgresql_agent_test_db"
dsn = "postgresql://postgres@localhost:5432/postgres"
ddl = """\
CREATE TABLE IF NOT EXISTS customer (
    customer_id SERIAL NOT NULL,
    first_name VARCHAR(45) NOT NULL,
    last_name VARCHAR(45) NOT NULL,
    email VARCHAR(50),
    CONSTRAINT customer_pkey PRIMARY KEY (customer_id)
    )
"""
def prepare_db():
    with psycopg.connect(dsn, autocommit=True) as cnn:
        with cnn.cursor() as cr:
            cr.execute(f'DROP DATABASE IF EXISTS {db_name} WITH (FORCE)')
            cr.execute(f'CREATE DATABASE {db_name}')
            cr.execute(f"""
                {ddl}
                """)

def clean_up_db():
    with psycopg.connect(dsn, autocommit=True) as cnn:
        with cnn.cursor() as cr:
            cr.execute(f'DROP DATABASE IF EXISTS {db_name}')

@pytest.mark.skipif(
    skip or skip_openai,
    reason="dependency is not installed OR requested to skip",
)
def test_postgresql_agent():
    config_list = config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )

    def termination_msg(x):
        return isinstance(x, dict) and "TERMINATE" == str(x.get("content", ""))[-9:].upper()

    admin = PostgreSqlAgent(
        "admin",
        is_termination_msg=termination_msg,
        max_consecutive_auto_reply=5,
        human_input_mode="NEVER",
        default_auto_reply="Reply `TERMINATE` if the task is done.",
        dsn=dsn
    )

    ASSISTANT_SYSTEM_MESSAGE = f"""\
    You are a polite, smart and helpful AI assistant which also an expert in SQL with PostgreSQL dialect.
    Your tasks is assist user to query data from a database with the following DDL:    
        {ddl}

    ### RULES
    When generating sql query always follow these rules:
        1. The database is a PostgreSQL database.
        2. Always limit the result to less than 20 records.
        3. Only generate sql query to retrieve data, never update data or the database structure.
        4. Never make query to retrieve all columns, i.e., do not use asterisks. Always specify the intended columns.

    In this conversation following applies:
        1. Reply with sql query blocks if you want to query data.
        2. The sql bot cannot provide any other feedback or perform any other action beyond executing the sql query.
        3. The sql bot also can't modify your sql query. So, do not give incomplete SQL statement which requires the bot to modify.
        4. Do not use a sql query block if it's not intended to be executed by the sql bot.
        5. When using sql query, you must indicate the script type in the sql query block.
        6. The sql query block must indicate it's a sql query by adding a language hint like the following:
            ```sql
            [replace this text including the square brackets with your sql query]
            ```
        7. Only one sql query block is for one sql query. Do not put multiple sql queries in one sql query block.
        
    """

    assistant = AssistantAgent(
        name="assistant",
        system_message=ASSISTANT_SYSTEM_MESSAGE,
        llm_config={
            "timeout": 600,
            "seed": 42,
            "config_list": config_list,
        },
    )

    assistant.reset()
    admin.reset()

    question = "How many customer are in the database?"

    admin.initiate_chat(assistant, message=question)
    extractor = MarkdownCodeExtractor()
    code_blocks = extractor.extract_code_blocks(admin.chat_messages[assistant][1]["content"])
    assert len(code_blocks) > 0
    assert code_blocks[0].language == "sql"

@pytest.mark.skipif(
    skip,
    reason="dependency is not installed",
)
def test_postgresql_query_executor():
    executor = PostgreSqlQueryExecutor(dsn)

    code_blocks = executor.code_extractor.extract_code_blocks("""
        ```
        SELECT * FROM customer
        ```
        """)

    result = executor.execute_code_blocks(code_blocks)
    assert result.exit_code == -1 # no sql hint

    code_blocks = executor.code_extractor.extract_code_blocks("""
        ```sql
        SELECT * FROM customer
        ```
        """)

    result = executor.execute_code_blocks(code_blocks)
    assert result.exit_code == 0 # select query is allowed
    
    code_blocks = executor.code_extractor.extract_code_blocks("""
        ```sql
        DROP TABLE customer
        ```
        """)

    result = executor.execute_code_blocks(code_blocks)
    assert result.exit_code == -1 # drop query is allowed

    code_blocks = executor.code_extractor.extract_code_blocks("""
        ```sql
        DELETE FROM customer
        ```
        """)

    result = executor.execute_code_blocks(code_blocks)
    assert result.exit_code == -1 # delete query is not allowed

    code_blocks = executor.code_extractor.extract_code_blocks("""
        ```sql
        UPDATE customer SET first_name = "MUST NOT HAPPENED"
        ```
        """)

    result = executor.execute_code_blocks(code_blocks)
    assert result.exit_code == -1 # update query is not allowed

    code_blocks = executor.code_extractor.extract_code_blocks("""
        ```sql
        INSERT INTO customer (first_name, last_name) VALUES ("MUST", "NOT HAPPENED")
        ```
        """)

    result = executor.execute_code_blocks(code_blocks)
    assert result.exit_code == -1 # insert query is not allowed

@pytest.fixture(autouse=True)
def run_around_tests():
    prepare_db()
    yield
    clean_up_db()

    
if __name__ == "__main__":
    test_postgresql_agent()
    test_postgresql_query_executor()
