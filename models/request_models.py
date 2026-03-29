from pydantic import BaseModel
from typing import List, Optional

class QuestionGenerationRequest(BaseModel):
    topic: str
    difficulty: str
    question_types: List[str]
    number_of_questions: int
    context_text: Optional[str] = None
    custom_structure: Optional[str] = None
    total_marks: Optional[int] = 40
    language: str = "English"
