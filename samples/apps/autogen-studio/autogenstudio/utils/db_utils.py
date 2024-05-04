# from .util import get_app_root
import os

from sqlmodel import Session

from ..database.dbmanager import DBManager
from ..datamodel import Agent, AgentType, Skill, Workflow, WorkflowAgentLink


def workflow_from_id(workflow_id: int, dbmanager: DBManager):
    workflow = dbmanager.get(Workflow, filters={"id": workflow_id}).data
    if not workflow or len(workflow) == 0:
        raise ValueError("The specified workflow does not exist.")
    workflow = workflow[0].model_dump(mode="json")
    workflow_agent_links = dbmanager.get(WorkflowAgentLink, filters={"workflow_id": workflow_id}).data

    def dump_agent(agent: Agent):
        exclude = []
        if agent.type != AgentType.groupchat:
            exclude = [
                "admin_name",
                "messages",
                "max_round",
                "admin_name",
                "speaker_selection_method",
                "allow_repeat_speaker",
            ]
        return agent.model_dump(warnings=False, mode="json", exclude=exclude)

    def get_agent(agent_id):
        with Session(dbmanager.engine) as session:
            agent: Agent = dbmanager.get_items(Agent, filters={"id": agent_id}, session=session).data[0]
            agent_dict = dump_agent(agent)
            agent_dict["skills"] = [Skill.model_validate(skill.model_dump(mode="json")) for skill in agent.skills]
            model_exclude = [
                "id",
                "agent_id",
                "created_at",
                "updated_at",
                "user_id",
                "description",
            ]
            models = [model.model_dump(mode="json", exclude=model_exclude) for model in agent.models]
            agent_dict["models"] = [model.model_dump(mode="json") for model in agent.models]

            if len(models) > 0:
                agent_dict["config"]["llm_config"] = agent_dict.get("config", {}).get("llm_config", {})
                llm_config = agent_dict["config"]["llm_config"]
                if llm_config:
                    llm_config["config_list"] = models
                agent_dict["config"]["llm_config"] = llm_config
            agent_dict["agents"] = [get_agent(agent.id) for agent in agent.agents]
            return agent_dict

    for link in workflow_agent_links:
        agent_dict = get_agent(link.agent_id)
        workflow[link.agent_type] = agent_dict
    return workflow
