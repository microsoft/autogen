import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, SQLModel, and_, create_engine, select

from .datamodel import (
    Agent,
    AgentLink,
    AgentModelLink,
    AgentSkillLink,
    Model,
    Response,
    Skill,
    Workflow,
    WorkflowAgentLink,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

valid_link_types = ["agent_model", "agent_skill", "agent_agent", "workflow_agent"]


class DBManager:
    """A class to manage database operations"""

    def __init__(self, engine_uri: str):
        self.engine = create_engine(engine_uri)
        self.session = Session(self.engine)

    def create_db_and_tables(self):
        """Create a new database and tables"""
        SQLModel.metadata.create_all(self.engine)

    def upsert(self, model: SQLModel):
        """Create a new entity"""
        # check if the model exists, update else add
        status = True
        model_class = type(model)

        try:
            existing_model = self.session.exec(select(model_class).where(model_class.id == model.id)).first()
            if existing_model:
                model.updated_at = datetime.now()
                for key, value in model.model_dump().items():
                    setattr(existing_model, key, value)
                model = existing_model
                self.session.add(model)
            else:
                self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
        except Exception as e:
            self.session.rollback()
            logger.error("Error while upserting %s", e)
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

    def get(
        self,
        model_class: SQLModel,
        filters: dict = None,
        return_json: bool = False,
        order: str = "desc",
    ):
        """List all entities for a user"""
        result = []
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
                result = [self._model_to_dict(row) for row in self.session.exec(statement).all()]
            else:
                result = self.session.exec(statement).all()
        except Exception as e:
            logger.error("Error while getting %s: %s", model_class, e)
        return result

    def delete(self, model_class: SQLModel, filters: dict = None):
        """Delete an entity"""
        row = None
        status_message = ""
        status = True
        try:
            if filters:
                conditions = [getattr(model_class, col) == value for col, value in filters.items()]
                row = self.session.exec(select(model_class).where(and_(*conditions))).all()
            else:
                row = self.session.exec(select(model_class)).all()
            if row:
                for row in row:
                    self.session.delete(row)
                self.session.commit()
                status_message = f"{model_class.__name__} Deleted Successfully"
            else:
                print(f"Row with filters {filters} not found")
                logger.info("Row with filters %s not found", filters)
                status_message = "Row not found"
        except Exception as e:
            self.session.rollback()
            logger.error("Error while deleting: %s", e)
            status_message = f"Error while deleting: {e}"
            status = False
        response = Response(
            message=status_message,
            status=status,
            data=None,
        )
        print(response)
        return response

    def get_linked_entities(
        self,
        link_type: str,
        primary_id: int,
        return_json: bool = False,
        agent_type: Optional[str] = None,
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
        try:
            if link_type == "agent_model":
                agent = self.get(Agent, filters={"id": primary_id})[0]  # get the agent
                linked_entities = agent.models
            elif link_type == "agent_skill":
                agent = self.get(Agent, filters={"id": primary_id})[0]
                linked_entities = agent.skills
            elif link_type == "agent_agent":
                agent = self.get(Agent, filters={"id": primary_id})[0]
                linked_entities = agent.agents
            elif link_type == "workflow_agent":
                linked_entities = self.session.exec(
                    select(Agent)
                    .join(WorkflowAgentLink)
                    .where(
                        WorkflowAgentLink.workflow_id == primary_id,
                        WorkflowAgentLink.agent_type == agent_type,
                    )
                ).all()
        except Exception as e:
            logger.error("Error while getting linked entities: %s", e)
            status_message = f"Error while getting linked entities: {e}"
            status = False
        if return_json:
            linked_entities = [self._model_to_dict(row) for row in linked_entities]

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
            try:
                if link_type == "agent_model":
                    primary_model = self.session.exec(select(Agent).where(Agent.id == primary_id)).first()
                    secondary_model = self.session.exec(select(Model).where(Model.id == secondary_id)).first()
                    if primary_model is None or secondary_model is None:
                        status = False
                        status_message = "One or both entity records do not exist."
                    else:
                        # check if the link already exists
                        existing_link = self.session.exec(
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
                    primary_model = self.session.exec(select(Agent).where(Agent.id == primary_id)).first()
                    secondary_model = self.session.exec(select(Agent).where(Agent.id == secondary_id)).first()
                    if primary_model is None or secondary_model is None:
                        status = False
                        status_message = "One or both entity records do not exist."
                    else:
                        # check if the link already exists
                        existing_link = self.session.exec(
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
                    primary_model = self.session.exec(select(Agent).where(Agent.id == primary_id)).first()
                    secondary_model = self.session.exec(select(Skill).where(Skill.id == secondary_id)).first()
                    if primary_model is None or secondary_model is None:
                        status = False
                        status_message = "One or both entity records do not exist."
                    else:
                        # check if the link already exists
                        existing_link = self.session.exec(
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
                    primary_model = self.session.exec(select(Workflow).where(Workflow.id == primary_id)).first()
                    secondary_model = self.session.exec(select(Agent).where(Agent.id == secondary_id)).first()
                    if primary_model is None or secondary_model is None:
                        status = False
                        status_message = "One or both entity records do not exist."
                    else:
                        # check if the link already exists
                        existing_link = self.session.exec(
                            select(WorkflowAgentLink).where(
                                WorkflowAgentLink.workflow_id == primary_id,
                                WorkflowAgentLink.agent_id == secondary_id,
                                WorkflowAgentLink.agent_type == agent_type,
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
                            )
                            self.session.add(workflow_agent_link)
                # add and commit the link
                self.session.add(primary_model)
                self.session.commit()
                status_message = (
                    f"{secondary_model.__class__.__name__} successfully linked "
                    f"to {primary_model.__class__.__name__}"
                )

            except Exception as e:
                self.session.rollback()
                logger.error("Error while linking: %s", e)
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

        if link_type not in valid_link_types:
            status = False
            status_message = f"Invalid link type: {link_type}. Valid link types are: {valid_link_types}"
            return Response(message=status_message, status=status)

        try:
            if link_type == "agent_model":
                existing_link = self.session.exec(
                    select(AgentModelLink).where(
                        AgentModelLink.agent_id == primary_id,
                        AgentModelLink.model_id == secondary_id,
                    )
                ).first()
            elif link_type == "agent_skill":
                existing_link = self.session.exec(
                    select(AgentSkillLink).where(
                        AgentSkillLink.agent_id == primary_id,
                        AgentSkillLink.skill_id == secondary_id,
                    )
                ).first()
            elif link_type == "agent_agent":
                existing_link = self.session.exec(
                    select(AgentLink).where(
                        AgentLink.parent_id == primary_id,
                        AgentLink.agent_id == secondary_id,
                    )
                ).first()
            elif link_type == "workflow_agent":
                existing_link = self.session.exec(
                    select(WorkflowAgentLink).where(
                        WorkflowAgentLink.workflow_id == primary_id,
                        WorkflowAgentLink.agent_id == secondary_id,
                        WorkflowAgentLink.agent_type == agent_type,
                    )
                ).first()

            if existing_link:
                self.session.delete(existing_link)
                self.session.commit()
                status_message = "Link removed successfully."
            else:
                status = False
                status_message = "Link does not exist."

        except Exception as e:
            self.session.rollback()
            logger.error("Error while unlinking: %s", e)
            status = False
            status_message = f"Error while unlinking due to an exception: {e}"

        return Response(message=status_message, status=status)
