from pydantic import BaseModel


class ArticleCreated(BaseModel):
    UserId: str
    article: str


class GraphicDesignCreated(BaseModel):
    UserId: str
    imageUri: str


class AuditText(BaseModel):
    UserId: str
    text: str


class AuditorAlert(BaseModel):
    UserId: str
    auditorAlertMessage: str
