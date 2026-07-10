"""Pydantic v2 request/response schemas. The request contract is the 23 RAW
UCI fields; engineered features are computed server-side and rejected here."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Applicant(BaseModel):
    model_config = ConfigDict(extra="forbid")  # reject unknown/engineered fields

    limit_bal: float = Field(ge=0)
    sex: int = Field(ge=1, le=2)
    education: int = Field(ge=0, le=6)
    marriage: int = Field(ge=0, le=3)
    age: int = Field(ge=18, le=120)
    pay_0: int = Field(ge=-2, le=9)
    pay_2: int = Field(ge=-2, le=9)
    pay_3: int = Field(ge=-2, le=9)
    pay_4: int = Field(ge=-2, le=9)
    pay_5: int = Field(ge=-2, le=9)
    pay_6: int = Field(ge=-2, le=9)
    bill_amt1: float
    bill_amt2: float
    bill_amt3: float
    bill_amt4: float
    bill_amt5: float
    bill_amt6: float
    pay_amt1: float = Field(ge=0)
    pay_amt2: float = Field(ge=0)
    pay_amt3: float = Field(ge=0)
    pay_amt4: float = Field(ge=0)
    pay_amt5: float = Field(ge=0)
    pay_amt6: float = Field(ge=0)

    def to_raw_row(self) -> dict:
        """Return a dict keyed by original UCI column names for score_batch."""
        return {name.upper(): getattr(self, name) for name in self.__class__.model_fields}


class PredictResponse(BaseModel):
    risk_score: float
    risk_band: str
    probability: float
    model_version: str
    prediction_id: str | None = None


class ExplainFactor(BaseModel):
    feature: str
    friendly: str
    contribution: float
    direction: str


class ExplainResponse(BaseModel):
    risk_score: float
    risk_band: str
    model_version: str
    top_factors: list[ExplainFactor]


class BatchPredictRequest(BaseModel):
    applicants: list[Applicant] = Field(min_length=1, max_length=1000)


class BatchPredictResponse(BaseModel):
    model_version: str
    count: int
    results: list[PredictResponse]
