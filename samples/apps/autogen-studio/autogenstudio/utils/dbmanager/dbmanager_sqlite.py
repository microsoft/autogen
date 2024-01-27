import json
import logging
import sqlite3
import threading
import os
from .idbmanager import IDBManager
from typing import Any, List, Dict, Optional, Tuple
from ...datamodel import AgentFlowSpec, AgentWorkFlowConfig, Gallery, Message, Model, Session, Skill


MODELS_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS models (
                id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                model TEXT,
                api_key TEXT,
                base_url TEXT,
                api_type TEXT,
                api_version TEXT,
                description TEXT,
                UNIQUE (id, user_id)
            )
            """


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


class SqliteDBManager(IDBManager):
    """
    A database manager class that handles the creation and interaction with an SQLite database.
    """

    def __init__(self) -> None:
        """
        Initializes the DBManager object.
        """

    def init_db(self, path: str = "database.sqlite", **kwargs: Any) -> None:
        """
        Initializes the database by creating necessary tables.

        Args:
            path (str): The file path to the SQLite database file.
            **kwargs: Additional keyword arguments to pass to the sqlite3.connect method.
        """

        self.path = path
        # check if the database exists, if not create it
        # self.reset_db()
        if not os.path.exists(self.path):
            logger.info("Creating database")
             # Connect to the database (or create a new one if it doesn't exist)
            self.conn = sqlite3.connect(path, check_same_thread=False, **kwargs)
            self.cursor = self.conn.cursor()

            # Create the models table
            self.cursor.execute(MODELS_TABLE_SQL)

            # Create the messages table
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
                models = data["models"]
                for model in models:
                    model = Model(**model)
                    self.cursor.execute(
                        "INSERT INTO models (id, user_id, timestamp, model, api_key, base_url, api_type, api_version, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            model.id,
                            "default",
                            model.timestamp,
                            model.model,
                            model.api_key,
                            model.base_url,
                            model.api_type,
                            model.api_version,
                            model.description,
                        ),
                    )

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
        Commits the current transaction Modelto the database.
        """
        self.conn.commit()

    def close(self) -> None:
        """
        Closes the database connection.
        """
        self.conn.close()


    def get_models(self, user_id: str) -> List[dict]:
        """
        Get all models for a given user from the database.

        Args:
            user_id: The user id to get models for

        Returns:
            A list  of model configurations
        """
        query = "SELECT * FROM models WHERE user_id = ? OR user_id = ?"
        args = (user_id, "default")
        results = self.query(query, args, return_json=True)
        return results


    def upsert_model(self, model: Model) -> List[dict]:
        """
        Insert or update a model configuration in the database.

        Args:
            model: The Model object containing model configuration data

        Returns:
            A list  of model configurations
        """

        # Check if the model config with the provided id already exists in the database
        existing_model = self.get_item_by_field("models", "id", model.id)

        if existing_model:
            # If the model config exists, update it with the new data
            updated_data = {
                "model": model.model,
                "api_key": model.api_key,
                "base_url": model.base_url,
                "api_type": model.api_type,
                "api_version": model.api_version,
                "user_id": model.user_id,
                "timestamp": model.timestamp,
                "description": model.description,
            }
            self.update_item("models", model.id, updated_data)
        else:
            # If the model config does not exist, insert a new one
            query = """
                INSERT INTO models (id, user_id, timestamp, model, api_key, base_url, api_type, api_version, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            args = (
                model.id,
                model.user_id,
                model.timestamp,
                model.model,
                model.api_key,
                model.base_url,
                model.api_type,
                model.api_version,
                model.description,
            )
            self.query(query=query, args=args)

        # Return the inserted or updated model config
        models = self.get_models(model.user_id)
        return models


    def delete_model(self, model: Model) -> List[dict]:
        """
        Delete a model configuration from the database where id = model.id and user_id = model.user_id.

        Args:
            model: The Model object containing model configuration data

        Returns:
            A list  of model configurations
        """

        query = "DELETE FROM models WHERE id = ? AND user_id = ?"
        args = (model.id, model.user_id)
        self.query(query=query, args=args)

        # Return the remaining model configs
        models = self.get_models(model.user_id)
        return models


    def create_message(self, message: Message) -> None:
        """
        Save a message in the database using the provided database manager.

        :param message: The Message object containing message data
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
        self.query(query=query, args=args)


    def get_messages(self, user_id: str, session_id: str) -> List[dict]:
        """
        Load messages for a specific user and session from the database, sorted by timestamp.

        :param user_id: The ID of the user whose messages are to be loaded
        :param session_id: The ID of the session whose messages are to be loaded

        :return: A list of dictionaries, each representing a message
        """
        query = "SELECT * FROM messages WHERE user_id = ? AND session_id = ?"
        args = (user_id, session_id)
        result = self.query(query=query, args=args, return_json=True)
        # Sort by timestamp ascending
        result = sorted(result, key=lambda k: k["timestamp"], reverse=False)
        return result


    def get_sessions(self, user_id: str) -> List[dict]:
        """
        Load sessions for a specific user from the database, sorted by timestamp.

        :param user_id: The ID of the user whose sessions are to be loaded
        :return: A list of dictionaries, each representing a session
        """
        query = "SELECT * FROM sessions WHERE user_id = ?"
        args = (user_id,)
        result = self.query(query=query, args=args, return_json=True)
        # Sort by timestamp ascending
        result = sorted(result, key=lambda k: k["timestamp"], reverse=True)
        for row in result:
            row["flow_config"] = json.loads(row["flow_config"])
        return result


    def create_session(self, user_id: str, session: Session) -> List[dict]:
        """
        Create a new session for a specific user in the database.

        :param user_id: The ID of the user whose session is to be created
        :return: A list of dictionaries, each representing a session
        """
        query = "INSERT INTO sessions (user_id, id, timestamp, flow_config) VALUES (?, ?, ?,?)"
        args = (session.user_id, session.id, session.timestamp, json.dumps(session.flow_config.dict()))
        self.query(query=query, args=args)
        sessions = self.get_sessions(user_id=user_id)

        return sessions


    def delete_session(self, session: Session) -> List[dict]:
        """
        Delete a specific session  and all messages for that session in the database.

        :param session: The Session object containing session data
        :return: A list of the remaining sessions
        """

        query = "DELETE FROM sessions WHERE id = ?"
        args = (session.id,)
        self.query(query=query, args=args)

        query = "DELETE FROM messages WHERE session_id = ?"
        args = (session.id,)
        self.query(query=query, args=args)

        return self.get_sessions(user_id=session.user_id)


    def create_gallery(self, session: Session, tags: List[str] = []) -> Gallery:
        """
        Publish a session to the gallery table in the database. Fetches the session messages first, then saves session and messages object to the gallery database table.
        :param session: The Session object containing session data
        :param tags: A list of tags to associate with the session
        :return: A gallery object containing the session and messages objects
        """

        messages = self.get_messages(user_id=session.user_id, session_id=session.id)
        gallery_item = Gallery(session=session, messages=messages, tags=tags)
        query = "INSERT INTO gallery (id, session, messages, tags, timestamp) VALUES (?, ?, ?, ?,?)"
        args = (
            gallery_item.id,
            json.dumps(gallery_item.session.dict()),
            json.dumps([message.dict() for message in gallery_item.messages]),
            json.dumps(gallery_item.tags),
            gallery_item.timestamp,
        )
        self.query(query=query, args=args)
        return gallery_item


    def get_gallery(self, gallery_id) -> List[Gallery]:
        """
        Load gallery items from the database, sorted by timestamp. If gallery_id is provided, only the gallery item with the matching gallery_id will be returned.

        :param gallery_id: The ID of the gallery item to be loaded
        :return: A list of Gallery objects
        """

        if gallery_id:
            query = "SELECT * FROM gallery WHERE id = ?"
            args = (gallery_id,)
        else:
            query = "SELECT * FROM gallery"
            args = ()
        result = self.query(query=query, args=args, return_json=True)
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


    def get_skills(self, user_id: str) -> List[Skill]:
        """
        Load skills from the database, sorted by timestamp. Load skills where id = user_id or user_id = default.

        :param user_id: The ID of the user whose skills are to be loaded
        :return: A list of Skill objects
        """

        query = "SELECT * FROM skills WHERE user_id = ? OR user_id = ?"
        args = (user_id, "default")
        result = self.query(query=query, args=args, return_json=True)
        # Sort by timestamp ascending
        result = sorted(result, key=lambda k: k["timestamp"], reverse=True)
        skills = []
        for row in result:
            skill = Skill(**row)
            skills.append(skill)
        return skills


    def upsert_skill(self, skill: Skill) -> List[Skill]:
        """
        Insert or update a skill for a specific user in the database.

        If the skill with the given ID already exists, it will be updated with the new data.
        Otherwise, a new skill will be created.

        :param  skill: The Skill object containing skill data
        :return: A list of dictionaries, each representing a skill
        """

        existing_skill = self.get_item_by_field("skills", "id", skill.id)

        if existing_skill:
            updated_data = {
                "user_id": skill.user_id,
                "timestamp": skill.timestamp,
                "content": skill.content,
                "title": skill.title,
                "file_name": skill.file_name,
            }
            self.update_item("skills", skill.id, updated_data)
        else:
            query = "INSERT INTO skills (id, user_id, timestamp, content, title, file_name) VALUES (?, ?, ?, ?, ?, ?)"
            args = (skill.id, skill.user_id, skill.timestamp, skill.content, skill.title, skill.file_name)
            self.query(query=query, args=args)

        skills = self.get_skills(user_id=skill.user_id)

        return skills


    def delete_skill(self, skill: Skill) -> List[Skill]:
        """
        Delete a skill for a specific user in the database.

        :param  skill: The Skill object containing skill data
        :return: A list of dictionaries, each representing a skill
        """
        # delete where id = skill.id and user_id = skill.user_id
        query = "DELETE FROM skills WHERE id = ? AND user_id = ?"
        args = (skill.id, skill.user_id)
        self.query(query=query, args=args)

        return self.get_skills(user_id=skill.user_id)


    def delete_message(self, 
        user_id: str, msg_id: str, session_id: str, delete_all: bool = False
    ) -> List[dict]:
        """
        Delete a specific message or all messages for a user and session from the database.

        :param user_id: The ID of the user whose messages are to be deleted
        :param msg_id: The ID of the specific message to be deleted (ignored if delete_all is True)
        :param session_id: The ID of the session whose messages are to be deleted
        :param delete_all: If True, all messages for the user will be deleted
        :return: A list of the remaining messages if not all were deleted, otherwise an empty list
        """

        if delete_all:
            query = "DELETE FROM messages WHERE user_id = ? AND session_id = ?"
            args = (user_id, session_id)
            self.query(query=query, args=args)
            return []
        else:
            query = "DELETE FROM messages WHERE user_id = ? AND msg_id = ? AND session_id = ?"
            args = (user_id, msg_id, session_id)
            self.query(query=query, args=args)
            messages = self.get_messages(user_id=user_id, session_id=session_id)
            return messages


    def get_agents(self, user_id: str) -> List[AgentFlowSpec]:
        """
        Load agents from the database, sorted by timestamp. Load agents where id = user_id or user_id = default.

        :param user_id: The ID of the user whose agents are to be loaded
        :return: A list of AgentFlowSpec objects
        """

        query = "SELECT * FROM agents WHERE user_id = ? OR user_id = ?"
        args = (user_id, "default")
        result = self.query(query=query, args=args, return_json=True)
        # Sort by timestamp ascending
        result = sorted(result, key=lambda k: k["timestamp"], reverse=True)
        agents = []
        for row in result:
            row["config"] = json.loads(row["config"])
            row["skills"] = json.loads(row["skills"] or "[]")
            agent = AgentFlowSpec(**row)
            agents.append(agent)
        return agents


    def upsert_agent(self, agent_flow_spec: AgentFlowSpec) -> List[Dict[str, Any]]:
        """
        Insert or update an agent for a specific user in the database.

        If the agent with the given ID already exists, it will be updated with the new data.
        Otherwise, a new agent will be created.

        :param agent_flow_spec: The AgentFlowSpec object containing agent configuration
        :return: A list of dictionaries, each representing an agent after insertion or update
        """

        existing_agent = self.get_item_by_field("agents", "id", agent_flow_spec.id)

        if existing_agent:
            updated_data = {
                "user_id": agent_flow_spec.user_id,
                "timestamp": agent_flow_spec.timestamp,
                "config": json.dumps(agent_flow_spec.config.dict()),
                "type": agent_flow_spec.type,
                "description": agent_flow_spec.description,
                "skills": json.dumps([x.dict() for x in agent_flow_spec.skills] if agent_flow_spec.skills else []),
            }
            self.update_item("agents", agent_flow_spec.id, updated_data)
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
            self.query(query=query, args=args)

        agents = self.get_agents(user_id=agent_flow_spec.user_id)
        return agents


    def delete_agent(self, agent: AgentFlowSpec) -> List[Dict[str, Any]]:
        """
        Delete an agent for a specific user from the database.

        :param agent: The AgentFlowSpec object containing agent configuration
        :return: A list of dictionaries, each representing an agent after deletion
        """

        # delete based on agent.id and agent.user_id
        query = "DELETE FROM agents WHERE id = ? AND user_id = ?"
        args = (agent.id, agent.user_id)
        self.query(query=query, args=args)

        return self.get_agents(user_id=agent.user_id)


    def get_item_by_field(self, table: str, field: str, value: Any) -> Optional[Dict[str, Any]]:
        query = f"SELECT * FROM {table} WHERE {field} = ?"
        args = (value,)
        result = self.query(query=query, args=args)
        return result[0] if result else None


    def update_item(self, table: str, item_id: str, updated_data: Dict[str, Any]) -> None:
        set_clause = ", ".join([f"{key} = ?" for key in updated_data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE id = ?"
        args = (*updated_data.values(), item_id)
        self.query(query=query, args=args)


    def get_workflows(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Load workflows for a specific user from the database, sorted by timestamp.

        :param user_id: The ID of the user whose workflows are to be loaded
        :return: A list of dictionaries, each representing a workflow
        """
        query = "SELECT * FROM workflows WHERE user_id = ? OR user_id = ?"
        args = (user_id, "default")
        result = self.query(query=query, args=args, return_json=True)
        # Sort by timestamp ascending
        result = sorted(result, key=lambda k: k["timestamp"], reverse=True)
        workflows = []
        for row in result:
            row["sender"] = json.loads(row["sender"])
            row["receiver"] = json.loads(row["receiver"])
            workflow = AgentWorkFlowConfig(**row)
            workflows.append(workflow)
        return workflows


    def upsert_workflow(self, workflow: AgentWorkFlowConfig) -> List[Dict[str, Any]]:
        """
        Insert or update a workflow for a specific user in the database.

        If the workflow with the given ID already exists, it will be updated with the new data.
        Otherwise, a new workflow will be created.

        :param workflow: The AgentWorkFlowConfig object containing workflow data
        :return: A list of dictionaries, each representing a workflow after insertion or update
        """
        existing_workflow = self.get_item_by_field("workflows", "id", workflow.id)

        # print(workflow.receiver)

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
            self.update_item("workflows", workflow.id, updated_data)
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
            self.query(query=query, args=args)

        return self.get_workflows(user_id=workflow.user_id)


    def delete_workflow(self, workflow: AgentWorkFlowConfig) -> List[Dict[str, Any]]:
        """
        Delete a workflow for a specific user from the database. If the workflow does not exist, do nothing.

        :param workflow: The AgentWorkFlowConfig object containing workflow data
        :return: A list of dictionaries, each representing a workflow after deletion
        """

        # delete where workflow.id =id and workflow.user_id = user_id

        query = "DELETE FROM workflows WHERE id = ? AND user_id = ?"
        args = (workflow.id, workflow.user_id)
        self.query(query=query, args=args)

        return self.get_workflows(user_id=workflow.user_id)
