from pydantic import BaseModel


class ArticleCreated(BaseModel):
    user_id: str
    article: str


class GraphicDesignCreated(BaseModel):
    user_id: str
    image_uri: str


class AuditText(BaseModel):
    user_id: str
    text: str


class AuditorAlert(BaseModel):
    user_id: str
    auditor_alert_message: str
