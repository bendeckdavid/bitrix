from pydantic import BaseModel


class NewConversation(BaseModel):
    title: str


class NewMessage(BaseModel):
    text: str
