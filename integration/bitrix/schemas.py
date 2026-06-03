from pydantic import BaseModel


class NewMessage(BaseModel):
    conversation_id: str
    text: str
    sender: str = ""
    system: bool = False
    channel: str = ""
    account: str = ""


class QuantumMessage(BaseModel):
    user_hash: str
    message: str
    message_channel: str = ""
    user_data: dict | None = None
