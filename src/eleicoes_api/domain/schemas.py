from pydantic import BaseModel, Field


class CandidateResult(BaseModel):
    number: int = Field(ge=0)
    name: str
    party: str | None = None
    votes: int = Field(ge=0)


class ElectionResults(BaseModel):
    year: int = Field(ge=1900)
    office: str
    state: str | None = None
    candidates: list[CandidateResult]


class CandidateVotesByState(BaseModel):
    year: int = Field(ge=1900)
    office: str
    turn: int = Field(ge=1, le=2)

    candidate_number: int
    candidate_name: str
    party: str | None = None

    total_votes: int = Field(ge=0)
    votes_by_state: dict[str, int]
