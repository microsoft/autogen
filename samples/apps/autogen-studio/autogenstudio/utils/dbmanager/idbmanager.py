from abc import ABC, abstractmethod
from typing import Any, List, Dict, Tuple, Optional
from ...datamodel import AgentFlowSpec, AgentWorkFlowConfig, Gallery, Message, Model, Session, Skill

class IDBManager(ABC):

    @abstractmethod
    def __init__(self, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def reset_db(self):
        pass

    @abstractmethod
    def init_db(self, path, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def init_db(self, host, port, db_name, user, password, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def query(self, query: str, args: Tuple = (), return_json: bool = False) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def commit(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def get_models(self, user_id: str) -> List[dict]:
        pass
   
    @abstractmethod
    def upsert_model(self, model: Model) -> List[dict]:
        pass
    
    @abstractmethod
    def delete_model(self, model: Model) -> List[dict]:
        pass

    @abstractmethod
    def create_message(self, message: Message) -> None:
        pass

    @abstractmethod
    def get_messages(self, user_id: str, session_id: str) -> List[dict]:
        pass
    

    @abstractmethod
    def get_sessions(self, user_id: str) -> List[dict]:
        pass

    @abstractmethod
    def create_session(self, user_id: str, session: Session) -> List[dict]:
        pass

    @abstractmethod
    def delete_session(self, session: Session) -> List[dict]:
        pass

    @abstractmethod
    def create_gallery(self, session: Session, tags: List[str] = []) -> Gallery:
        pass

    @abstractmethod
    def get_gallery(self, gallery_id) -> List[Gallery]:
        pass

    @abstractmethod
    def get_skills(self, user_id: str) -> List[Skill]:
        pass
        

    @abstractmethod
    def upsert_skill(self, skill: Skill) -> List[Skill]:
        pass
    

    @abstractmethod
    def delete_skill(self, skill: Skill) -> List[Skill]:
        pass

    @abstractmethod
    def delete_message(self, user_id: str, msg_id: str, session_id: str, delete_all: bool = False) -> List[dict]:
        pass

    @abstractmethod
    def get_agents(self, user_id: str) -> List[AgentFlowSpec]:
        pass

    @abstractmethod
    def upsert_agent(self, agent_flow_spec: AgentFlowSpec) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete_agent(self, agent: AgentFlowSpec) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_item_by_field(self, table: str, field: str, value: Any) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_item(self, table: str, item_id: str, updated_data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_workflows(self, user_id: str) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def upsert_workflow(self, workflow: AgentWorkFlowConfig) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def delete_workflow(self, workflow: AgentWorkFlowConfig) -> List[Dict[str, Any]]:
        pass
        