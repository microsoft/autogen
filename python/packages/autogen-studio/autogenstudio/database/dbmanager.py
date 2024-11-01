import threading
from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import exc
from sqlmodel import Session, SQLModel, and_, create_engine, select

from ..datamodel import (
    Agent,
    AgentModelLink,
    AgentToolLink,
    Model,
    Response,
    Team,
    TeamAgentLink,
    Tool,
)
# from .dbutils import init_db_samples

valid_link_types = ["agent_model", "agent_tool", "team_agent"]


class TeamAgentMap(SQLModel):
    agent: Agent
    link: TeamAgentLink


class DBManager:
    """A class to manage database operations"""

    _init_lock = threading.Lock()

    def __init__(self, engine_uri: str):
        connection_args = {
            "check_same_thread": True} if "sqlite" in engine_uri else {}
        self.engine = create_engine(engine_uri, connect_args=connection_args)

    def create_db_and_tables(self):
        """Create a new database and tables"""
        with self._init_lock:
            try:
                SQLModel.metadata.create_all(self.engine)
                try:
                    # init_db_samples(self)
                    pass
                except Exception as e:
                    logger.info(
                        "Error while initializing database samples: " + str(e))
            except Exception as e:
                logger.info("Error while creating database tables:" + str(e))

    def upsert(self, model: SQLModel):
        """Create or update an entity"""
        status = True
        model_class = type(model)
        existing_model = None

        with Session(self.engine) as session:
            try:
                existing_model = session.exec(
                    select(model_class).where(model_class.id == model.id)).first()
                if existing_model:
                    model.updated_at = datetime.now()
                    for key, value in model.model_dump().items():
                        setattr(existing_model, key, value)
                    model = existing_model  # Use the updated existing model
                    session.add(model)
                else:
                    session.add(model)
                session.commit()
                session.refresh(model)
            except Exception as e:
                session.rollback()
                logger.error("Error while updating/creating " +
                             str(model_class.__name__) + ": " + str(e))
                status = False

        return Response(
            message=(
                f"{model_class.__name__} Updated Successfully"
                if existing_model
                else f"{model_class.__name__} Created Successfully"
            ),
            status=status,
            data=model.model_dump(),
        )

    def _model_to_dict(self, model_obj):
        return {col.name: getattr(model_obj, col.name) for col in model_obj.__table__.columns}

    def get(
        self,
        model_class: SQLModel,
        filters: dict = None,
        return_json: bool = False,
        order: str = "desc",
    ):
        """List entities"""
        with Session(self.engine) as session:
            result = []
            status = True
            status_message = ""

            try:
                statement = select(model_class)
                if filters:
                    conditions = [getattr(model_class, col) ==
                                  value for col, value in filters.items()]
                    statement = statement.where(and_(*conditions))

                if hasattr(model_class, "created_at") and order:
                    order_by_clause = getattr(
                        model_class.created_at, order)()  # Dynamically apply asc/desc
                    statement = statement.order_by(order_by_clause)

                items = session.exec(statement).all()
                result = [self._model_to_dict(
                    item) if return_json else item for item in items]
                status_message = f"{model_class.__name__} Retrieved Successfully"
            except Exception as e:
                session.rollback()
                status = False
                status_message = f"Error while fetching {model_class.__name__}"
                logger.error("Error while getting items: " +
                             str(model_class.__name__) + " " + str(e))

            return Response(message=status_message, status=status, data=result)

    def delete(self, model_class: SQLModel, filters: dict = None):
        """Delete an entity"""
        status_message = ""
        status = True

        with Session(self.engine) as session:
            try:
                statement = select(model_class)
                if filters:
                    conditions = [
                        getattr(model_class, col) == value for col, value in filters.items()]
                    statement = statement.where(and_(*conditions))

                rows = session.exec(statement).all()

                if rows:
                    for row in rows:
                        session.delete(row)
                    session.commit()
                    status_message = f"{model_class.__name__} Deleted Successfully"
                else:
                    status_message = "Row not found"
                    logger.info(f"Row with filters {filters} not found")

            except exc.IntegrityError as e:
                session.rollback()
                status = False
                status_message = f"Integrity error: The {model_class.__name__} is linked to another entity and cannot be deleted. {e}"
                # Log the specific integrity error
                logger.error(status_message)
            except Exception as e:
                session.rollback()
                status = False
                status_message = f"Error while deleting: {e}"
                logger.error(status_message)

        return Response(message=status_message, status=status, data=None)

    def get_linked_entities(
        self,
        link_type: str,
        primary_id: int,
        return_json: bool = False,
    ):
        """Get linked entities based on link type and primary ID."""

        linked_entities = []

        if link_type not in valid_link_types:
            return Response(message=f"Invalid link type: {link_type}", status=False, data=[])

        with Session(self.engine) as session:
            try:
                if link_type == "agent_model":
                    agent = session.get(Agent, primary_id)
                    linked_entities = agent.models if agent else []
                elif link_type == "agent_tool":
                    agent = session.get(Agent, primary_id)
                    linked_entities = agent.tools if agent else []
                elif link_type == "team_agent":
                    linked_entities = session.exec(
                        select(TeamAgentLink, Agent)
                        .join(Agent, TeamAgentLink.agent_id == Agent.id)
                        .where(TeamAgentLink.team_id == primary_id)
                    ).all()
                    linked_entities = [TeamAgentMap(agent=agent, link=link) for link,
                                       agent in linked_entities]
                    linked_entities.sort(key=lambda x: x.link.sequence)

                if return_json:
                    linked_entities = [
                        entity.model_dump() for entity in linked_entities]

            except Exception as e:
                return Response(
                    message=f"Error getting linked entities: {e}", status=False, data=[]
                )

        return Response(
            message="Linked entities retrieved successfully", status=True, data=linked_entities
        )

    def link(
        self,
        link_type: str,
        primary_id: int,
        secondary_id: int,
        sequence: Optional[int] = None,  # For team_agent links
    ):
        """Link two entities."""

        if link_type not in valid_link_types:
            return Response(
                message=f"Invalid link type: {link_type}", status=False
            )

        with Session(self.engine) as session:
            try:
                if link_type == "agent_model":
                    primary_model = session.get(Agent, primary_id)
                    secondary_model = session.get(Model, secondary_id)
                    link_table = AgentModelLink
                elif link_type == "agent_tool":
                    primary_model = session.get(Agent, primary_id)
                    secondary_model = session.get(Tool, secondary_id)
                    link_table = AgentToolLink
                elif link_type == "team_agent":
                    primary_model = session.get(Team, primary_id)
                    secondary_model = session.get(Agent, secondary_id)
                    link_table = TeamAgentLink

                if not primary_model or not secondary_model:
                    return Response(
                        message="One or both entities do not exist", status=False
                    )

                # Check for existing link (adapt as needed for sequence)
                existing_link = session.exec(
                    select(link_table).where(
                        link_table.agent_id == primary_id
                        if hasattr(link_table, "agent_id") and hasattr(link_table, "primary_id")
                        else link_table.team_id == primary_id,
                        getattr(link_table, "model_id", getattr(
                            link_table, "tool_id", getattr(link_table, "agent_id"))) == secondary_id
                    )
                ).first()

                if existing_link:
                    return Response(message="Link already exists", status=False)

                if link_type == "team_agent":
                    new_link = link_table(
                        team_id=primary_id, agent_id=secondary_id, sequence=sequence)
                    session.add(new_link)
                else:
                    getattr(primary_model, link_type.split("_")[1] +
                            "s").append(secondary_model)  # type: ignore

                session.commit()

                return Response(message="Entities linked successfully", status=True)

            except Exception as e:
                session.rollback()
                return Response(message=f"Error linking entities: {e}", status=False)

    def unlink(
        self, link_type: str, primary_id: int, secondary_id: int, sequence: Optional[int] = None
    ):
        """Unlink two entities."""

        if link_type not in valid_link_types:
            return Response(message=f"Invalid link type: {link_type}", status=False)

        with Session(self.engine) as session:
            try:
                if link_type == "agent_model":
                    link_table = AgentModelLink
                elif link_type == "agent_tool":
                    link_table = AgentToolLink
                elif link_type == "team_agent":
                    link_table = TeamAgentLink
                # Find existing link
                statement = select(link_table).where(
                    getattr(link_table, "agent_id",
                            link_table.team_id) == primary_id,
                    getattr(link_table, "model_id", getattr(
                        link_table, "tool_id", link_table.agent_id)) == secondary_id
                )

                if link_type == "team_agent" and sequence is not None:  # add sequence to filter
                    statement = statement.where(
                        link_table.sequence == sequence)

                existing_link = session.exec(statement).first()

                if not existing_link:
                    return Response(message="Link does not exist", status=False)

                session.delete(existing_link)
                session.commit()

                return Response(message="Entities unlinked successfully", status=True)

            except Exception as e:
                session.rollback()
                return Response(message=f"Error unlinking entities: {e}", status=False)
