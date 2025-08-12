from pydantic import BaseModel
from typing import List
import operator
from typing_extensions import Annotated

class QueryResults(BaseModel):
    title: str = None
    url: str = None
    resume: str = None

class ReportState(BaseModel):
    user_input: str = None
    final_response: str = None
    final_response_edited: str = None
    queries: List[str] = []
    queries_results: Annotated[List[QueryResults], operator.add]