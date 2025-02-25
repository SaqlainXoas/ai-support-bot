#core/evaluator.py

from pydantic import BaseModel

class EvaluationResult(BaseModel):
    score: float
    needs_escalation: bool

def evaluate_response(query: str, response: str) -> EvaluationResult:
    query_lower = query.lower()
    if any(keyword in query_lower for keyword in ["order", "status", "track"]):
        return EvaluationResult(score=0.9, needs_escalation=False)
    if len(query.split()) < 3:
        return EvaluationResult(score=0.9, needs_escalation=False)
    # If the generated response is too short, it might indicate low confidence—escalate.
    if len(response.strip()) < 20:
        return EvaluationResult(score=0.4, needs_escalation=True)
    # Otherwise, assume a safe response.
    return EvaluationResult(score=0.8, needs_escalation=False)
