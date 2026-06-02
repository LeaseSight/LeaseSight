import os
# Wipe it completely out of system memory immediately
os.environ.pop("GOOGLE_API_KEY", None)
os.environ.pop("GEMINI_API_KEY", None)

# Force the system key to match our working REST token from .env
# If your code uses dotenv, manually load it here first
from dotenv import load_dotenv
load_dotenv()

working_key = os.getenv("GEMINI_API_KEY", "")
os.environ["GOOGLE_API_KEY"] = working_key
os.environ["GEMINI_API_KEY"] = working_key

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


load_dotenv()

GEMINI_EVAL_MODEL = os.getenv("GEMINI_EVAL_MODEL", "gemini-3.1-flash-lite")
LIVE_EVAL_MODEL = "gemini-3.1-flash-lite"
BASE_DIR = Path(__file__).resolve().parents[2]
BENCHMARKS_PATH = BASE_DIR / "data" / "benchmarks.json"
FAILED_CASES_PATH = BASE_DIR / "data" / "failed_cases.json"

ACADEMIC_BENCHMARK = {
    "paper_title": "CUAD Legal Dataset Benchmark",
    "precision": 0.44,
    "recall": 0.48,
    "f1_score": 0.46,
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


def _configure_gemini_model(deps: Dict[str, Any], model_name: str = GEMINI_EVAL_MODEL) -> Any:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required to run DeepEval evaluations.")

    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["GEMINI_API_KEY"] = api_key
    return deps["GeminiModel"](
        model_name=model_name,
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


def _load_benchmark_config() -> Dict[str, Any]:
    try:
        with open(BENCHMARKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return ACADEMIC_BENCHMARK.copy()


def _load_failed_cases() -> List[Dict[str, str]]:
    if not FAILED_CASES_PATH.exists():
        return []
    try:
        with open(FAILED_CASES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _classify_failure(
    golden: GoldenLeaseCase,
    faithfulness: float,
    answer_relevance: float,
    context_recall: float,
) -> str:
    context_text = " ".join(golden.retrieval_context).strip()
    if not context_text or len(context_text) < 80:
        return "OCR_ERROR"
    if context_recall < 0.7:
        return "RETRIEVAL_ERROR"
    if faithfulness < 0.7 or answer_relevance < 0.7:
        return "GENERATION_ERROR"
    return "GENERATION_ERROR"


def _append_failed_case(
    golden: GoldenLeaseCase,
    faithfulness: float,
    answer_relevance: float,
    context_recall: float,
):
    FAILED_CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    failed_cases = _load_failed_cases()
    failed_cases.append(
        {
            "user_query": golden.input,
            "generated_output": golden.actual_output,
            "failure_reason": _classify_failure(
                golden,
                faithfulness,
                answer_relevance,
                context_recall,
            ),
        }
    )
    with open(FAILED_CASES_PATH, "w", encoding="utf-8") as f:
        json.dump(failed_cases, f, indent=2)


def _run_evaluation_sync() -> Dict[str, Any]:
    deps = _load_deepeval_dependencies()
    model = _configure_gemini_model(deps)
    benchmark = _load_benchmark_config()
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

        faithfulness = float(metrics["faithfulness"].score or 0.0)
        answer_relevance = float(metrics["answer_relevance"].score or 0.0)
        context_recall = float(metrics["context_recall"].score or 0.0)
        if faithfulness < 0.7 or answer_relevance < 0.7:
            _append_failed_case(
                golden,
                faithfulness,
                answer_relevance,
                context_recall,
            )

    case_count = len(GOLDEN_DATASET)
    averages = {
        metric_name: round(total / case_count, 2)
        for metric_name, total in totals.items()
    }

    return {
        "deepeval_metrics": averages,
        "academic_benchmark": {
            "paper_title": benchmark["paper_title"],
            "precision": benchmark["precision"],
            "recall": benchmark["recall"],
            "f1_score": benchmark["f1_score"],
            "paper_f1_score": benchmark["f1_score"],
            "leasesight_f1_score": round(
                (
                    averages["faithfulness"]
                    + averages["answer_relevance"]
                    + averages["context_recall"]
                )
                / 3,
                2,
            ),
        },
        "failed_cases": _load_failed_cases(),
    }


async def run_system_evaluation() -> Dict[str, Any]:
    return await asyncio.to_thread(_run_evaluation_sync)


def evaluate_live_document(
    user_query: str,
    generated_output: str,
    retrieved_chunks: List[str],
    user_id: str = None,
) -> Dict[str, float | bool | str]:
    try:
        deps = _load_deepeval_dependencies()
        test_case = deps["LLMTestCase"](
            input=user_query,
            actual_output=generated_output,
            retrieval_context=retrieved_chunks or [],
        )
        model = _configure_gemini_model(deps, model_name=LIVE_EVAL_MODEL)
        metrics = {
            "faithfulness": deps["FaithfulnessMetric"](
                threshold=0.6,
                model=model,
                include_reason=False,
            ),
            "answer_relevance": deps["AnswerRelevanceMetric"](
                threshold=0.6,
                model=model,
                include_reason=False,
            ),
        }

        for metric in metrics.values():
            metric.measure(test_case)

        faithfulness = float(metrics["faithfulness"].score or 0.0)
        answer_relevance = float(metrics["answer_relevance"].score or 0.0)
        groundedness_index = (faithfulness + answer_relevance) / 2
        return {
            "faithfulness": faithfulness,
            "answer_relevance": answer_relevance,
            "groundedness_index": groundedness_index,
            "is_trusted": faithfulness >= 0.6 and answer_relevance >= 0.6,
        }
    except Exception as e:
        return {
            "faithfulness": 0.0,
            "answer_relevance": 0.0,
            "groundedness_index": 0.0,
            "is_trusted": False,
            "error": f"Live evaluation unavailable: {str(e)[:240]}",
        }
