import json
import logging
import sqlite3
import threading
import os
from typing import Any, List, Dict, Optional, Tuple
from ..datamodel import AgentFlowSpec, AgentWorkFlowConfig, Gallery, Message, Session, Skill


MESSAGES_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS messages (
                user_id TEXT NOT NULL,
                session_id TEXT,
                root_msg_id TEXT NOT NULL,
                msg_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp DATETIME,
                UNIQUE (user_id, root_msg_id, msg_id)
            )
            """

SESSIONS_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                flow_config TEXT,
                UNIQUE (user_id, id)
            )
            """

SKILLS_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                content TEXT,
                title TEXT,
                file_name TEXT,
                UNIQUE (id, user_id)
            )
            """
AGENTS_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS agents (

                id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                config TEXT,
                type TEXT,
                skills TEXT,
                description TEXT,
                UNIQUE (id, user_id)
            )
            """

WORKFLOWS_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                sender TEXT,
                receiver TEXT,
                type TEXT,
                name TEXT,
                description TEXT,
                summary_method TEXT,
                UNIQUE (id, user_id)
            )
            """

GALLERY_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS gallery (
                id TEXT NOT NULL,
                session TEXT,
                messages TEXT,
                tags TEXT,
                timestamp DATETIME NOT NULL,
                UNIQUE ( id)
            )
            """


lock = threading.Lock()
logger = logging.getLogger()


class DBManager:
    """
    A database manager class that handles the creation and interaction with an SQLite database.
    """

    def __init__(self, path: str = "database.sqlite", **kwargs: Any) -> None:
        """
        Initializes the DBManager object, creates a database if it does not exist, and establishes a connection.

        Args:
            path (str): The file path to the SQLite database file.
            **kwargs: Additional keyword arguments to pass to the sqlite3.connect method.
        """

        self.path = path
        # check if the database exists, if not create it
        # self.reset_db()
        if not os.path.exists(self.path):
            logger.info("Creating database")
            self.init_db(path=self.path, **kwargs)

        try:
            self.conn = sqlite3.connect(self.path, check_same_thread=False, **kwargs)
            self.cursor = self.conn.cursor()
        except Exception as e:
            logger.error("Error connecting to database: %s", e)
            raise e

    def reset_db(self):
        """
        Reset the database by deleting the database file and creating a new one.
        """
        print("resetting db")
        if os.path.exists(self.path):
            os.remove(self.path)
        self.init_db(path=self.path)

    def init_db(self, path: str = "database.sqlite", **kwargs: Any) -> None:
        """
        Initializes the database by creating necessary tables.

        Args:
            path (str): The file path to the SQLite database file.
            **kwargs: Additional keyword arguments to pass to the sqlite3.connect method.
        """
        # Connect to the database (or create a new one if it doesn't exist)
        self.conn = sqlite3.connect(path, check_same_thread=False, **kwargs)
        self.cursor = self.conn.cursor()

        # Create the table with the specified columns, appropriate data types, and a UNIQUE constraint on (root_msg_id, msg_id)
        self.cursor.execute(MESSAGES_TABLE_SQL)

        # Create a sessions table
        self.cursor.execute(SESSIONS_TABLE_SQL)

        # Create a  skills
        self.cursor.execute(SKILLS_TABLE_SQL)

        # Create a gallery table
        self.cursor.execute(GALLERY_TABLE_SQL)

        # Create a agents table
        self.cursor.execute(AGENTS_TABLE_SQL)

        # Create a workflows table
        self.cursor.execute(WORKFLOWS_TABLE_SQL)

        # init skills table with content of defaultskills.json in current directory
        current_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(current_dir, "dbdefaults.json"), "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
            skills = data["skills"]
            agents = data["agents"]
            for skill in skills:
                skill = Skill(**skill)

                self.cursor.execute(
                    "INSERT INTO skills (id, user_id, timestamp, content, title, file_name) VALUES (?, ?, ?, ?, ?, ?)",
                    (skill.id, "default", skill.timestamp, skill.content, skill.title, skill.file_name),
                )
            for agent in agents:
                agent = AgentFlowSpec(**agent)
                agent.skills = [skill.dict() for skill in agent.skills] if agent.skills else None
                self.cursor.execute(
                    "INSERT INTO agents (id, user_id, timestamp, config, type, skills, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        agent.id,
                        "default",
                        agent.timestamp,
                        json.dumps(agent.config.dict()),
                        agent.type,
                        json.dumps(agent.skills),
                        agent.description,
                    ),
                )

            for workflow in data["workflows"]:
                workflow = AgentWorkFlowConfig(**workflow)
                self.cursor.execute(
                    "INSERT INTO workflows (id, user_id, timestamp, sender, receiver, type, name, description, summary_method) VALUES (?, ?, ?, ?, ?, ?, ?, ?,?)",
                    (
                        workflow.id,
                        "default",
                        workflow.timestamp,
                        json.dumps(workflow.sender.dict()),
                        json.dumps(workflow.receiver.dict()),
                        workflow.type,
                        workflow.name,
                        workflow.description,
                        workflow.summary_method,
                    ),
                )

        # Commit the changes and close the connection
        self.conn.commit()

    def query(self, query: str, args: Tuple = (), return_json: bool = False) -> List[Dict[str, Any]]:
        """
        Executes a given SQL query and returns the results.

        Args:
            query (str): The SQL query to execute.
            args (Tuple): The arguments to pass to the SQL query.
            return_json (bool): If True, the results will be returned as a list of dictionaries.

        Returns:
            List[Dict[str, Any]]: The result of the SQL query.
        """
        try:
            with lock:
                self.cursor.execute(query, args)
                result = self.cursor.fetchall()
                self.commit()
                if return_json:
                    result = [dict(zip([key[0] for key in self.cursor.description], row)) for row in result]
                return result
        except Exception as e:
            logger.error("Error running query with query %s and args %s: %s", query, args, e)
            raise e

    def commit(self) -> None:
        """
        Commits the current transaction to the database.
        """
        self.conn.commit()

    def close(self) -> None:
        """
        Closes the database connection.
        """
        self.conn.close()


def create_message(message: Message, dbmanager: DBManager) -> None:
    """
    Save a message in the database using the provided database manager.

    :param message: The Message object containing message data
    :param dbmanager: The DBManager instance used to interact with the database
    """
    query = "INSERT INTO messages (user_id, root_msg_id, msg_id, role, content, metadata, timestamp, session_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    args = (
        message.user_id,
        message.root_msg_id,
        message.msg_id,
        message.role,
        message.content,
        message.metadata,
        message.timestamp,
        message.session_id,
    )
    dbmanager.query(query=query, args=args)


def get_messages(user_id: str, session_id: str, dbmanager: DBManager) -> List[dict]:
    """
    Load messages for a specific user and session from the database, sorted by timestamp.

    :param user_id: The ID of the user whose messages are to be loaded
    :param session_id: The ID of the session whose messages are to be loaded
    :param dbmanager: The DBManager instance to interact with the database

    :return: A list of dictionaries, each representing a message
    """
    query = "SELECT * FROM messages WHERE user_id = ? AND session_id = ?"
    args = (user_id, session_id)
    result = dbmanager.query(query=query, args=args, return_json=True)
    # Sort by timestamp ascending
    result = sorted(result, key=lambda k: k["timestamp"], reverse=False)
    return result


def get_sessions(user_id: str, dbmanager: DBManager) -> List[dict]:
    """
    Load sessions for a specific user from the database, sorted by timestamp.

    :param user_id: The ID of the user whose sessions are to be loaded
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing a session
    """
    query = "SELECT * FROM sessions WHERE user_id = ?"
    args = (user_id,)
    result = dbmanager.query(query=query, args=args, return_json=True)
    # Sort by timestamp ascending
    result = sorted(result, key=lambda k: k["timestamp"], reverse=True)
    for row in result:
        row["flow_config"] = json.loads(row["flow_config"])
    return result


def create_session(user_id: str, session: Session, dbmanager: DBManager) -> List[dict]:
    """
    Create a new session for a specific user in the database.

    :param user_id: The ID of the user whose session is to be created
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing a session
    """
    query = "INSERT INTO sessions (user_id, id, timestamp, flow_config) VALUES (?, ?, ?,?)"
    args = (session.user_id, session.id, session.timestamp, json.dumps(session.flow_config.dict()))
    dbmanager.query(query=query, args=args)
    sessions = get_sessions(user_id=user_id, dbmanager=dbmanager)

    return sessions


def delete_session(session: Session, dbmanager: DBManager) -> List[dict]:
    """
    Delete a specific session  and all messages for that session in the database.

    :param session: The Session object containing session data
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of the remaining sessions
    """

    query = "DELETE FROM sessions WHERE id = ?"
    args = (session.id,)
    dbmanager.query(query=query, args=args)

    query = "DELETE FROM messages WHERE session_id = ?"
    args = (session.id,)
    dbmanager.query(query=query, args=args)

    return get_sessions(user_id=session.user_id, dbmanager=dbmanager)


def create_gallery(session: Session, dbmanager: DBManager, tags: List[str] = []) -> Gallery:
    """
    Publish a session to the gallery table in the database. Fetches the session messages first, then saves session and messages object to the gallery database table.
    :param session: The Session object containing session data
    :param dbmanager: The DBManager instance used to interact with the database
    :param tags: A list of tags to associate with the session
    :return: A gallery object containing the session and messages objects
    """

    messages = get_messages(user_id=session.user_id, session_id=session.id, dbmanager=dbmanager)
    gallery_item = Gallery(session=session, messages=messages, tags=tags)
    query = "INSERT INTO gallery (id, session, messages, tags, timestamp) VALUES (?, ?, ?, ?,?)"
    args = (
        gallery_item.id,
        json.dumps(gallery_item.session.dict()),
        json.dumps([message.dict() for message in gallery_item.messages]),
        json.dumps(gallery_item.tags),
        gallery_item.timestamp,
    )
    dbmanager.query(query=query, args=args)
    return gallery_item


def get_gallery(gallery_id, dbmanager: DBManager) -> List[Gallery]:
    """
    Load gallery items from the database, sorted by timestamp. If gallery_id is provided, only the gallery item with the matching gallery_id will be returned.

    :param gallery_id: The ID of the gallery item to be loaded
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of Gallery objects
    """

    if gallery_id:
        query = "SELECT * FROM gallery WHERE id = ?"
        args = (gallery_id,)
    else:
        query = "SELECT * FROM gallery"
        args = ()
    result = dbmanager.query(query=query, args=args, return_json=True)
    # Sort by timestamp ascending
    result = sorted(result, key=lambda k: k["timestamp"], reverse=True)
    gallery = []
    for row in result:
        gallery_item = Gallery(
            id=row["id"],
            session=Session(**json.loads(row["session"])),
            messages=[Message(**message) for message in json.loads(row["messages"])],
            tags=json.loads(row["tags"]),
            timestamp=row["timestamp"],
        )
        gallery.append(gallery_item)
    return gallery


def get_skills(user_id: str, dbmanager: DBManager) -> List[Skill]:
    """
    Load skills from the database, sorted by timestamp. Load skills where id = user_id or user_id = default.

    :param user_id: The ID of the user whose skills are to be loaded
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of Skill objects
    """

    query = "SELECT * FROM skills WHERE user_id = ? OR user_id = ?"
    args = (user_id, "default")
    result = dbmanager.query(query=query, args=args, return_json=True)
    # Sort by timestamp ascending
    result = sorted(result, key=lambda k: k["timestamp"], reverse=True)
    skills = []
    for row in result:
        skill = Skill(**row)
        skills.append(skill)
    return skills


def upsert_skill(skill: Skill, dbmanager: DBManager) -> List[Skill]:
    """
    Insert or update a skill for a specific user in the database.

    If the skill with the given ID already exists, it will be updated with the new data.
    Otherwise, a new skill will be created.

    :param  skill: The Skill object containing skill data
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing a skill
    """

    existing_skill = get_item_by_field("skills", "id", skill.id, dbmanager)

    if existing_skill:
        updated_data = {
            "user_id": skill.user_id,
            "timestamp": skill.timestamp,
            "content": skill.content,
            "title": skill.title,
            "file_name": skill.file_name,
        }
        update_item("skills", skill.id, updated_data, dbmanager)
    else:
        query = "INSERT INTO skills (id, user_id, timestamp, content, title, file_name) VALUES (?, ?, ?, ?, ?, ?)"
        args = (skill.id, skill.user_id, skill.timestamp, skill.content, skill.title, skill.file_name)
        dbmanager.query(query=query, args=args)

    skills = get_skills(user_id=skill.user_id, dbmanager=dbmanager)

    return skills


def delete_skill(skill: Skill, dbmanager: DBManager) -> List[Skill]:
    """
    Delete a skill for a specific user in the database.

    :param  skill: The Skill object containing skill data
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing a skill
    """
    # delete where id = skill.id and user_id = skill.user_id
    query = "DELETE FROM skills WHERE id = ? AND user_id = ?"
    args = (skill.id, skill.user_id)
    dbmanager.query(query=query, args=args)

    return get_skills(user_id=skill.user_id, dbmanager=dbmanager)


def delete_message(
    user_id: str, msg_id: str, session_id: str, dbmanager: DBManager, delete_all: bool = False
) -> List[dict]:
    """
    Delete a specific message or all messages for a user and session from the database.

    :param user_id: The ID of the user whose messages are to be deleted
    :param msg_id: The ID of the specific message to be deleted (ignored if delete_all is True)
    :param session_id: The ID of the session whose messages are to be deleted
    :param dbmanager: The DBManager instance to interact with the database
    :param delete_all: If True, all messages for the user will be deleted
    :return: A list of the remaining messages if not all were deleted, otherwise an empty list
    """

    if delete_all:
        query = "DELETE FROM messages WHERE user_id = ? AND session_id = ?"
        args = (user_id, session_id)
        dbmanager.query(query=query, args=args)
        return []
    else:
        query = "DELETE FROM messages WHERE user_id = ? AND msg_id = ? AND session_id = ?"
        args = (user_id, msg_id, session_id)
        dbmanager.query(query=query, args=args)
        messages = get_messages(user_id=user_id, session_id=session_id, dbmanager=dbmanager)
        return messages


def get_agents(user_id: str, dbmanager: DBManager) -> List[AgentFlowSpec]:
    """
    Load agents from the database, sorted by timestamp. Load agents where id = user_id or user_id = default.

    :param user_id: The ID of the user whose agents are to be loaded
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of AgentFlowSpec objects
    """

    query = "SELECT * FROM agents WHERE user_id = ? OR user_id = ?"
    args = (user_id, "default")
    result = dbmanager.query(query=query, args=args, return_json=True)
    # Sort by timestamp ascending
    result = sorted(result, key=lambda k: k["timestamp"], reverse=True)
    agents = []
    for row in result:
        row["config"] = json.loads(row["config"])
        row["skills"] = json.loads(row["skills"] or "[]")
        agent = AgentFlowSpec(**row)
        agents.append(agent)
    return agents


def upsert_agent(agent_flow_spec: AgentFlowSpec, dbmanager: DBManager) -> List[Dict[str, Any]]:
    """
    Insert or update an agent for a specific user in the database.

    If the agent with the given ID already exists, it will be updated with the new data.
    Otherwise, a new agent will be created.

    :param agent_flow_spec: The AgentFlowSpec object containing agent configuration
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing an agent after insertion or update
    """

    existing_agent = get_item_by_field("agents", "id", agent_flow_spec.id, dbmanager)

    if existing_agent:
        updated_data = {
            "user_id": agent_flow_spec.user_id,
            "timestamp": agent_flow_spec.timestamp,
            "config": json.dumps(agent_flow_spec.config.dict()),
            "type": agent_flow_spec.type,
            "description": agent_flow_spec.description,
            "skills": json.dumps([x.dict() for x in agent_flow_spec.skills] if agent_flow_spec.skills else []),
        }
        update_item("agents", agent_flow_spec.id, updated_data, dbmanager)
    else:
        query = "INSERT INTO agents (id, user_id, timestamp, config, type, description, skills) VALUES (?, ?, ?, ?, ?, ?, ?)"
        config_json = json.dumps(agent_flow_spec.config.dict())
        args = (
            agent_flow_spec.id,
            agent_flow_spec.user_id,
            agent_flow_spec.timestamp,
            config_json,
            agent_flow_spec.type,
            agent_flow_spec.description,
            json.dumps([x.dict() for x in agent_flow_spec.skills] if agent_flow_spec.skills else []),
        )
        dbmanager.query(query=query, args=args)

    agents = get_agents(user_id=agent_flow_spec.user_id, dbmanager=dbmanager)
    return agents


def delete_agent(agent: AgentFlowSpec, dbmanager: DBManager) -> List[Dict[str, Any]]:
    """
    Delete an agent for a specific user from the database.

    :param agent: The AgentFlowSpec object containing agent configuration
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing an agent after deletion
    """

    # delete based on agent.id and agent.user_id
    query = "DELETE FROM agents WHERE id = ? AND user_id = ?"
    args = (agent.id, agent.user_id)
    dbmanager.query(query=query, args=args)

    return get_agents(user_id=agent.user_id, dbmanager=dbmanager)


def get_item_by_field(table: str, field: str, value: Any, dbmanager: DBManager) -> Optional[Dict[str, Any]]:
    query = f"SELECT * FROM {table} WHERE {field} = ?"
    args = (value,)
    result = dbmanager.query(query=query, args=args)
    return result[0] if result else None


def update_item(table: str, item_id: str, updated_data: Dict[str, Any], dbmanager: DBManager) -> None:
    set_clause = ", ".join([f"{key} = ?" for key in updated_data.keys()])
    query = f"UPDATE {table} SET {set_clause} WHERE id = ?"
    args = (*updated_data.values(), item_id)
    dbmanager.query(query=query, args=args)


def get_workflows(user_id: str, dbmanager: DBManager) -> List[Dict[str, Any]]:
    """
    Load workflows for a specific user from the database, sorted by timestamp.

    :param user_id: The ID of the user whose workflows are to be loaded
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing a workflow
    """
    query = "SELECT * FROM workflows WHERE user_id = ? OR user_id = ?"
    args = (user_id, "default")
    result = dbmanager.query(query=query, args=args, return_json=True)
    # Sort by timestamp ascending
    result = sorted(result, key=lambda k: k["timestamp"], reverse=True)
    workflows = []
    for row in result:
        row["sender"] = json.loads(row["sender"])
        row["receiver"] = json.loads(row["receiver"])
        workflow = AgentWorkFlowConfig(**row)
        workflows.append(workflow)
    return workflows


def upsert_workflow(workflow: AgentWorkFlowConfig, dbmanager: DBManager) -> List[Dict[str, Any]]:
    """
    Insert or update a workflow for a specific user in the database.

    If the workflow with the given ID already exists, it will be updated with the new data.
    Otherwise, a new workflow will be created.

    :param workflow: The AgentWorkFlowConfig object containing workflow data
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing a workflow after insertion or update
    """
    existing_workflow = get_item_by_field("workflows", "id", workflow.id, dbmanager)

    if existing_workflow:
        updated_data = {
            "user_id": workflow.user_id,
            "timestamp": workflow.timestamp,
            "sender": json.dumps(workflow.sender.dict()),
            "receiver": json.dumps(
                [receiver.dict() for receiver in workflow.receiver]
                if isinstance(workflow.receiver, list)
                else workflow.receiver.dict()
            ),
            "type": workflow.type,
            "name": workflow.name,
            "description": workflow.description,
            "summary_method": workflow.summary_method,
        }
        update_item("workflows", workflow.id, updated_data, dbmanager)
    else:
        query = "INSERT INTO workflows (id, user_id, timestamp, sender, receiver, type, name, description, summary_method) VALUES (?, ?, ?, ?, ?, ?, ?, ?,?)"
        args = (
            workflow.id,
            workflow.user_id,
            workflow.timestamp,
            json.dumps(workflow.sender.dict()),
            json.dumps(
                [receiver.dict() for receiver in workflow.receiver]
                if isinstance(workflow.receiver, list)
                else workflow.receiver.dict()
            ),
            workflow.type,
            workflow.name,
            workflow.description,
            workflow.summary_method,
        )
        dbmanager.query(query=query, args=args)

    return get_workflows(user_id=workflow.user_id, dbmanager=dbmanager)


def delete_workflow(workflow: AgentWorkFlowConfig, dbmanager: DBManager) -> List[Dict[str, Any]]:
    """
    Delete a workflow for a specific user from the database. If the workflow does not exist, do nothing.

    :param workflow: The AgentWorkFlowConfig object containing workflow data
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing a workflow after deletion
    """

    # delete where workflow.id =id and workflow.user_id = user_id

    query = "DELETE FROM workflows WHERE id = ? AND user_id = ?"
    args = (workflow.id, workflow.user_id)
    dbmanager.query(query=query, args=args)

    return get_workflows(user_id=workflow.user_id, dbmanager=dbmanager)
