import threading
from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import exc
from sqlmodel import Session, SQLModel, and_, create_engine, select

from ..datamodel import (
    Agent,
    AgentLink,
    AgentModelLink,
    AgentSkillLink,
    Model,
    Response,
    Skill,
    Workflow,
    WorkflowAgentLink,
    WorkflowAgentType,
)
from .utils import init_db_samples

valid_link_types = ["agent_model", "agent_skill", "agent_agent", "workflow_agent"]


class WorkflowAgentMap(SQLModel):
    agent: Agent
    link: WorkflowAgentLink


class DBManager:
    """A class to manage database operations"""

    _init_lock = threading.Lock()  # Class-level lock

    def __init__(self, engine_uri: str):
        connection_args = {"check_same_thread": True} if "sqlite" in engine_uri else {}
        self.engine = create_engine(engine_uri, connect_args=connection_args)
        # run_migration(engine_uri=engine_uri)

    def create_db_and_tables(self):
        """Create a new database and tables"""
        with self._init_lock:  # Use the lock
            try:
                SQLModel.metadata.create_all(self.engine)
                try:
                    init_db_samples(self)
                except Exception as e:
                    logger.info("Error while initializing database samples: " + str(e))
            except Exception as e:
                logger.info("Error while creating database tables:" + str(e))

    def upsert(self, model: SQLModel):
        """Create a new entity"""
        # check if the model exists, update else add
        status = True
        model_class = type(model)
        existing_model = None

        with Session(self.engine) as session:
            try:
                existing_model = session.exec(select(model_class).where(model_class.id == model.id)).first()
                if existing_model:
                    model.updated_at = datetime.now()
                    for key, value in model.model_dump().items():
                        setattr(existing_model, key, value)
                    model = existing_model
                    session.add(model)
                else:
                    session.add(model)
                session.commit()
                session.refresh(model)
            except Exception as e:
                session.rollback()
                logger.error("Error while updating " + str(model_class.__name__) + ": " + str(e))
                status = False

        response = Response(
            message=(
                f"{model_class.__name__} Updated Successfully "
                if existing_model
                else f"{model_class.__name__} Created Successfully"
            ),
            status=status,
            data=model.model_dump(),
        )

        return response

    def _model_to_dict(self, model_obj):
        return {col.name: getattr(model_obj, col.name) for col in model_obj.__table__.columns}

    def get_items(
        self,
        model_class: SQLModel,
        session: Session,
        filters: dict = None,
        return_json: bool = False,
        order: str = "desc",
    ):
        """List all entities"""
        result = []
        status = True
        status_message = ""

        try:
            if filters:
                conditions = [getattr(model_class, col) == value for col, value in filters.items()]
                statement = select(model_class).where(and_(*conditions))

                if hasattr(model_class, "created_at") and order:
                    if order == "desc":
                        statement = statement.order_by(model_class.created_at.desc())
                    else:
                        statement = statement.order_by(model_class.created_at.asc())
            else:
                statement = select(model_class)

            if return_json:
                result = [self._model_to_dict(row) for row in session.exec(statement).all()]
            else:
                result = session.exec(statement).all()
            status_message = f"{model_class.__name__} Retrieved Successfully"
        except Exception as e:
            session.rollback()
            status = False
            status_message = f"Error while fetching  {model_class.__name__}"
            logger.error("Error while getting items: " + str(model_class.__name__) + " " + str(e))

        response: Response = Response(
            message=status_message,
            status=status,
            data=result,
        )
        return response

    def get(
        self,
        model_class: SQLModel,
        filters: dict = None,
        return_json: bool = False,
        order: str = "desc",
    ):
        """List all entities"""

        with Session(self.engine) as session:
            response = self.get_items(model_class, session, filters, return_json, order)
        return response

    def delete(self, model_class: SQLModel, filters: dict = None):
        """Delete an entity"""
        row = None
        status_message = ""
        status = True

        with Session(self.engine) as session:
            try:
                if filters:
                    conditions = [getattr(model_class, col) == value for col, value in filters.items()]
                    row = session.exec(select(model_class).where(and_(*conditions))).all()
                else:
                    row = session.exec(select(model_class)).all()
                if row:
                    for row in row:
                        session.delete(row)
                    session.commit()
                    status_message = f"{model_class.__name__} Deleted Successfully"
                else:
                    print(f"Row with filters {filters} not found")
                    logger.info("Row with filters + filters + not found")
                    status_message = "Row not found"
            except exc.IntegrityError as e:
                session.rollback()
                logger.error("Integrity ... Error while deleting: " + str(e))
                status_message = f"The {model_class.__name__} is linked to another entity and cannot be deleted."
                status = False
            except Exception as e:
                session.rollback()
                logger.error("Error while deleting: " + str(e))
                status_message = f"Error while deleting: {e}"
                status = False
            response = Response(
                message=status_message,
                status=status,
                data=None,
            )
        return response

    def get_linked_entities(
        self,
        link_type: str,
        primary_id: int,
        return_json: bool = False,
        agent_type: Optional[str] = None,
        sequence_id: Optional[int] = None,
    ):
        """
        Get all entities linked to the primary entity.

        Args:
            link_type (str): The type of link to retrieve, e.g., "agent_model".
            primary_id (int): The identifier for the primary model.
            return_json (bool): Whether to return the result as a JSON object.

        Returns:
            List[SQLModel]: A list of linked entities.
        """

        linked_entities = []

        if link_type not in valid_link_types:
            return []

        status = True
        status_message = ""

        with Session(self.engine) as session:
            try:
                if link_type == "agent_model":
                    # get the agent
                    agent = self.get_items(Agent, filters={"id": primary_id}, session=session).data[0]
                    linked_entities = agent.models
                elif link_type == "agent_skill":
                    agent = self.get_items(Agent, filters={"id": primary_id}, session=session).data[0]
                    linked_entities = agent.skills
                elif link_type == "agent_agent":
                    agent = self.get_items(Agent, filters={"id": primary_id}, session=session).data[0]
                    linked_entities = agent.agents
                elif link_type == "workflow_agent":
                    linked_entities = session.exec(
                        select(WorkflowAgentLink, Agent)
                        .join(Agent, WorkflowAgentLink.agent_id == Agent.id)
                        .where(
                            WorkflowAgentLink.workflow_id == primary_id,
                        )
                    ).all()

                    linked_entities = [WorkflowAgentMap(agent=agent, link=link) for link, agent in linked_entities]
                    linked_entities = sorted(linked_entities, key=lambda x: x.link.sequence_id)  # type: ignore
            except Exception as e:
                logger.error("Error while getting linked entities: " + str(e))
                status_message = f"Error while getting linked entities: {e}"
                status = False
            if return_json:
                linked_entities = [row.model_dump() for row in linked_entities]

        response = Response(
            message=status_message,
            status=status,
            data=linked_entities,
        )

        return response

    def link(
        self,
        link_type: str,
        primary_id: int,
        secondary_id: int,
        agent_type: Optional[str] = None,
        sequence_id: Optional[int] = None,
    ) -> Response:
        """
        Link two entities together.

        Args:
            link_type (str): The type of link to create, e.g., "agent_model".
            primary_id (int): The identifier for the primary model.
            secondary_id (int): The identifier for the secondary model.
            agent_type (Optional[str]): The type of agent, e.g., "sender" or receiver.

        Returns:
            Response: The response of the linking operation, including success status and message.
        """

        # TBD verify that is creator of the primary entity being linked
        status = True
        status_message = ""
        primary_model = None
        secondary_model = None

        if link_type not in valid_link_types:
            status = False
            status_message = f"Invalid link type: {link_type}. Valid link types are: {valid_link_types}"
        else:
            with Session(self.engine) as session:
                try:
                    if link_type == "agent_model":
                        primary_model = session.exec(select(Agent).where(Agent.id == primary_id)).first()
                        secondary_model = session.exec(select(Model).where(Model.id == secondary_id)).first()
                        if primary_model is None or secondary_model is None:
                            status = False
                            status_message = "One or both entity records do not exist."
                        else:
                            # check if the link already exists
                            existing_link = session.exec(
                                select(AgentModelLink).where(
                                    AgentModelLink.agent_id == primary_id,
                                    AgentModelLink.model_id == secondary_id,
                                )
                            ).first()
                            if existing_link:  # link already exists
                                return Response(
                                    message=(
                                        f"{secondary_model.__class__.__name__} already linked "
                                        f"to {primary_model.__class__.__name__}"
                                    ),
                                    status=False,
                                )
                            else:
                                primary_model.models.append(secondary_model)
                    elif link_type == "agent_agent":
                        primary_model = session.exec(select(Agent).where(Agent.id == primary_id)).first()
                        secondary_model = session.exec(select(Agent).where(Agent.id == secondary_id)).first()
                        if primary_model is None or secondary_model is None:
                            status = False
                            status_message = "One or both entity records do not exist."
                        else:
                            # check if the link already exists
                            existing_link = session.exec(
                                select(AgentLink).where(
                                    AgentLink.parent_id == primary_id,
                                    AgentLink.agent_id == secondary_id,
                                )
                            ).first()
                            if existing_link:
                                return Response(
                                    message=(
                                        f"{secondary_model.__class__.__name__} already linked "
                                        f"to {primary_model.__class__.__name__}"
                                    ),
                                    status=False,
                                )
                            else:
                                primary_model.agents.append(secondary_model)

                    elif link_type == "agent_skill":
                        primary_model = session.exec(select(Agent).where(Agent.id == primary_id)).first()
                        secondary_model = session.exec(select(Skill).where(Skill.id == secondary_id)).first()
                        if primary_model is None or secondary_model is None:
                            status = False
                            status_message = "One or both entity records do not exist."
                        else:
                            # check if the link already exists
                            existing_link = session.exec(
                                select(AgentSkillLink).where(
                                    AgentSkillLink.agent_id == primary_id,
                                    AgentSkillLink.skill_id == secondary_id,
                                )
                            ).first()
                            if existing_link:
                                return Response(
                                    message=(
                                        f"{secondary_model.__class__.__name__} already linked "
                                        f"to {primary_model.__class__.__name__}"
                                    ),
                                    status=False,
                                )
                            else:
                                primary_model.skills.append(secondary_model)
                    elif link_type == "workflow_agent":
                        primary_model = session.exec(select(Workflow).where(Workflow.id == primary_id)).first()
                        secondary_model = session.exec(select(Agent).where(Agent.id == secondary_id)).first()
                        if primary_model is None or secondary_model is None:
                            status = False
                            status_message = "One or both entity records do not exist."
                        else:
                            # check if the link already exists
                            existing_link = session.exec(
                                select(WorkflowAgentLink).where(
                                    WorkflowAgentLink.workflow_id == primary_id,
                                    WorkflowAgentLink.agent_id == secondary_id,
                                    WorkflowAgentLink.agent_type == agent_type,
                                    WorkflowAgentLink.sequence_id == sequence_id,
                                )
                            ).first()
                            if existing_link:
                                return Response(
                                    message=(
                                        f"{secondary_model.__class__.__name__} already linked "
                                        f"to {primary_model.__class__.__name__}"
                                    ),
                                    status=False,
                                )
                            else:
                                # primary_model.agents.append(secondary_model)
                                workflow_agent_link = WorkflowAgentLink(
                                    workflow_id=primary_id,
                                    agent_id=secondary_id,
                                    agent_type=agent_type,
                                    sequence_id=sequence_id,
                                )
                                session.add(workflow_agent_link)
                    # add and commit the link
                    session.add(primary_model)
                    session.commit()
                    status_message = (
                        f"{secondary_model.__class__.__name__} successfully linked "
                        f"to {primary_model.__class__.__name__}"
                    )

                except Exception as e:
                    session.rollback()
                    logger.error("Error while linking: " + str(e))
                    status = False
                    status_message = f"Error while linking due to an exception: {e}"

        response = Response(
            message=status_message,
            status=status,
        )

        return response

    def unlink(
        self,
        link_type: str,
        primary_id: int,
        secondary_id: int,
        agent_type: Optional[str] = None,
        sequence_id: Optional[int] = 0,
    ) -> Response:
        """
        Unlink two entities.

        Args:
            link_type (str): The type of link to remove, e.g., "agent_model".
            primary_id (int): The identifier for the primary model.
            secondary_id (int): The identifier for the secondary model.
            agent_type (Optional[str]): The type of agent, e.g., "sender" or receiver.

        Returns:
            Response: The response of the unlinking operation, including success status and message.
        """
        status = True
        status_message = ""
        print("primary", primary_id, "secondary", secondary_id, "sequence", sequence_id, "agent_type", agent_type)

        if link_type not in valid_link_types:
            status = False
            status_message = f"Invalid link type: {link_type}. Valid link types are: {valid_link_types}"
            return Response(message=status_message, status=status)

        with Session(self.engine) as session:
            try:
                if link_type == "agent_model":
                    existing_link = session.exec(
                        select(AgentModelLink).where(
                            AgentModelLink.agent_id == primary_id,
                            AgentModelLink.model_id == secondary_id,
                        )
                    ).first()
                elif link_type == "agent_skill":
                    existing_link = session.exec(
                        select(AgentSkillLink).where(
                            AgentSkillLink.agent_id == primary_id,
                            AgentSkillLink.skill_id == secondary_id,
                        )
                    ).first()
                elif link_type == "agent_agent":
                    existing_link = session.exec(
                        select(AgentLink).where(
                            AgentLink.parent_id == primary_id,
                            AgentLink.agent_id == secondary_id,
                        )
                    ).first()
                elif link_type == "workflow_agent":
                    existing_link = session.exec(
                        select(WorkflowAgentLink).where(
                            WorkflowAgentLink.workflow_id == primary_id,
                            WorkflowAgentLink.agent_id == secondary_id,
                            WorkflowAgentLink.agent_type == agent_type,
                            WorkflowAgentLink.sequence_id == sequence_id,
                        )
                    ).first()

                if existing_link:
                    session.delete(existing_link)
                    session.commit()
                    status_message = "Link removed successfully."
                else:
                    status = False
                    status_message = "Link does not exist."

            except Exception as e:
                session.rollback()
                logger.error("Error while unlinking: " + str(e))
                status = False
                status_message = f"Error while unlinking due to an exception: {e}"

        return Response(message=status_message, status=status)
