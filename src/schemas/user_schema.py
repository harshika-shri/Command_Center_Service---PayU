from pydantic import BaseModel


class ManagerSummary(BaseModel):
    id: str
    name: str
    email: str
