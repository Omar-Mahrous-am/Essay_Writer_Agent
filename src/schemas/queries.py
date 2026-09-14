from typing import List
from pydantic import BaseModel


class Queries(BaseModel):
    queries: List[str]