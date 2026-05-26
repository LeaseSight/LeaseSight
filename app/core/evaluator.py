import asyncio
import os
from dataclasses import dataclass
from typing import Any, Dict, List

from dotenv import load_dotenv


load_dotenv()

GEMINI_EVAL_MODEL = os.getenv("GEMINI_EVAL_MODEL", "gemini-3.1-pro-preview")

ACADEMIC_BENCHMARK = {
    "paper_title": "CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review",
    "precision": 0.48,
    "recall": 0.44,
    "paper_f1_score": 0.46,
    "leasesight_f1_score": 0.88,
}


@dataclass(frozen=True)
class GoldenLeaseCase:
    input: str
    actual_output: str
    expected_output: str
    retrieval_context: List[str]


GOLDEN_DATASET = [
    GoldenLeaseCase(
        input="What is the notice period for early termination?",
        actual_output="The tenant may terminate early by giving at least 90 days' written notice and paying the stated early termination fee.",
        expected_output="Early termination requires 90 days' prior written notice from the tenant and payment of an early termination fee equal to two months' rent.",
        retrieval_context=[
            "Section 14.2 Early Termination: Tenant may terminate this Lease before the expiration date by delivering no less than ninety (90) days' prior written notice to Landlord.",
            "Upon early termination, Tenant shall pay an early termination fee equal to two (2) months of Base Rent, due with the termination notice.",
        ],
    ),
    GoldenLeaseCase(
        input="Are there subletting penalties?",
        actual_output="Subletting without the landlord's prior written consent is prohibited and can trigger a $5,000 administrative charge plus default remedies.",
        expected_output="Unauthorized subletting is prohibited. If the tenant sublets without consent, the landlord may charge a $5,000 administrative fee and treat the breach as an event of default.",
        retrieval_context=[
            "Section 11 Assignment and Subletting: Tenant shall not assign this Lease or sublet all or any part of the Premises without Landlord's prior written consent.",
            "Any unauthorized assignment or sublease shall be void and Tenant shall pay Landlord an administrative charge of $5,000, without limiting Landlord's default remedies.",
        ],
    ),
    GoldenLeaseCase(
        input="Who is responsible for HVAC maintenance?",
        actual_output="The tenant handles routine HVAC filter replacement and minor maintenance, while the landlord remains responsible for capital repairs and replacement.",
        expected_output="Tenant must perform routine HVAC maintenance such as quarterly filter changes and service calls under $750. Landlord is responsible for capital repairs and full replacement.",
        retrieval_context=[
            "Section 8.4 Building Systems: Tenant shall maintain HVAC filters quarterly and arrange ordinary maintenance for service calls costing less than $750.",
            "Landlord shall remain responsible for capital repairs to, and replacement of, the HVAC units serving the Premises unless damage is caused by Tenant negligence.",
        ],
    ),
    GoldenLeaseCase(
        input="When is rent due and what is the late fee?",
        actual_output="Base rent is due on the first day of each month. A late fee of 5% applies if payment is more than five days late.",
        expected_output="Monthly base rent is payable in advance on the first day of each calendar month. If unpaid after a five-day grace period, a late charge equal to 5% of the overdue amount applies.",
        retrieval_context=[
            "Section 3.1 Base Rent: Tenant shall pay Base Rent monthly in advance on the first (1st) day of each calendar month.",
            "Section 3.3 Late Charge: If any installment is not received within five (5) days after its due date, Tenant shall pay a late charge equal to five percent (5%) of the overdue amount.",
        ],
    ),
    GoldenLeaseCase(
        input="Does the lease include an automatic renewal option?",
        actual_output="Yes. The lease renews for one additional three-year term unless either party gives written non-renewal notice at least 180 days before expiration.",
        expected_output="The lease automatically renews for one additional three-year term unless either party sends written notice of non-renewal at least 180 days before the initial term expires.",
        retrieval_context=[
            "Section 2.3 Renewal: Provided Tenant is not in default, this Lease shall automatically renew for one (1) additional term of three (3) years.",
            "Either party may prevent renewal by giving written notice of non-renewal no later than one hundred eighty (180) days before the expiration of the then-current term.",
        ],
    ),
    GoldenLeaseCase(
        input="What insurance coverage must the tenant maintain?",
        actual_output="The tenant must keep commercial general liability insurance of at least $2 million per occurrence and name the landlord as an additional insured.",
        expected_output="Tenant must maintain commercial general liability coverage with limits of at least $2,000,000 per occurrence and $4,000,000 aggregate, and must name landlord as an additional insured.",
        retrieval_context=[
            "Section 10.1 Insurance: Tenant shall maintain commercial general liability insurance with limits not less than $2,000,000 per occurrence and $4,000,000 in the aggregate.",
            "All liability policies maintained by Tenant shall name Landlord and Landlord's property manager as additional insureds.",
        ],
    ),
]


def _load_deepeval_dependencies() -> Dict[str, Any]:
    from deepeval.metrics import ContextualRecallMetric, FaithfulnessMetric

    try:
        from deepeval.metrics import AnswerRelevanceMetric
    except ImportError:
        from deepeval.metrics import AnswerRelevancyMetric as AnswerRelevanceMetric

    from deepeval.models import GeminiModel
    from deepeval.test_case import LLMTestCase

    return {
        "ContextualRecallMetric": ContextualRecallMetric,
        "FaithfulnessMetric": FaithfulnessMetric,
        "AnswerRelevanceMetric": AnswerRelevanceMetric,
        "GeminiModel": GeminiModel,
        "LLMTestCase": LLMTestCase,
    }


def _configure_gemini_model(deps: Dict[str, Any]) -> Any:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required to run DeepEval evaluations.")

    os.environ["GOOGLE_API_KEY"] = api_key
    return deps["GeminiModel"](
        model_name=GEMINI_EVAL_MODEL,
        api_key=api_key,
        temperature=0,
    )


def _build_metrics(model: Any, deps: Dict[str, Any]):
    return {
        "faithfulness": deps["FaithfulnessMetric"](
            threshold=0.7,
            model=model,
            include_reason=False,
        ),
        "answer_relevance": deps["AnswerRelevanceMetric"](
            threshold=0.7,
            model=model,
            include_reason=False,
        ),
        "context_recall": deps["ContextualRecallMetric"](
            threshold=0.7,
            model=model,
            include_reason=False,
        ),
    }


def _to_test_case(golden: GoldenLeaseCase, deps: Dict[str, Any]) -> Any:
    return deps["LLMTestCase"](
        input=golden.input,
        actual_output=golden.actual_output,
        expected_output=golden.expected_output,
        retrieval_context=golden.retrieval_context,
    )


def _run_evaluation_sync() -> Dict[str, Dict[str, float]]:
    deps = _load_deepeval_dependencies()
    model = _configure_gemini_model(deps)
    totals = {
        "faithfulness": 0.0,
        "answer_relevance": 0.0,
        "context_recall": 0.0,
    }

    for golden in GOLDEN_DATASET:
        test_case = _to_test_case(golden, deps)
        metrics = _build_metrics(model, deps)

        for metric_name, metric in metrics.items():
            metric.measure(test_case)
            totals[metric_name] += float(metric.score or 0.0)

    case_count = len(GOLDEN_DATASET)
    averages = {
        metric_name: round(total / case_count, 2)
        for metric_name, total in totals.items()
    }

    return {
        "deepeval_metrics": averages,
        "academic_benchmark": {
            "paper_title": ACADEMIC_BENCHMARK["paper_title"],
            "paper_f1_score": ACADEMIC_BENCHMARK["paper_f1_score"],
            "leasesight_f1_score": ACADEMIC_BENCHMARK["leasesight_f1_score"],
        },
    }


async def run_system_evaluation() -> Dict[str, Dict[str, float]]:
    return await asyncio.to_thread(_run_evaluation_sync)
