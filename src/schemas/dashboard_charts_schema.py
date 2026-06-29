from pydantic import BaseModel


class ChartDataResponse(BaseModel):
    labels: list[str]
    values: list[int]
