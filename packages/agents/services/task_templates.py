from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

TASK_TYPES = ("summarization", "classification", "extraction", "short_answer")

TASK_TEMPLATES = [
    {
        "task_type": "summarization",
        "complexity": "medium",
        "sla_seconds": 180,
        "budget_class": "standard",
        "template": "Summarize in one sentence: What is one ethical use of AI?",
        "validation_rule": "length_and_content",
    },
    {
        "task_type": "classification",
        "complexity": "low",
        "sla_seconds": 120,
        "budget_class": "economy",
        "template": "Classify: Is sustainable compute usage beneficial? Answer yes or no.",
        "validation_rule": "binary",
    },
    {
        "task_type": "extraction",
        "complexity": "medium",
        "sla_seconds": 200,
        "budget_class": "standard",
        "template": "Extract the main compliance risk from: sharing customer PII with a third-party AI vendor. One sentence.",
        "validation_rule": "content",
    },
    {
        "task_type": "short_answer",
        "complexity": "low",
        "sla_seconds": 90,
        "budget_class": "economy",
        "template": "Short answer: What is agentic commerce in one phrase?",
        "validation_rule": "length",
    },
]

PRICE_BY_BUDGET = {
    "economy": {"xrp": "0.8", "usd": "0.012", "escrow_eth": "0.008"},
    "standard": {"xrp": "1.0", "usd": "0.015", "escrow_eth": "0.01"},
    "premium": {"xrp": "1.2", "usd": "0.018", "escrow_eth": "0.012"},
}


@dataclass
class TaskSpec:
    task_type: str
    complexity: str
    sla_seconds: int
    budget_class: str
    template: str
    validation_rule: str
    quoted_price_xrp: str = ""
    quoted_price_usd: str = ""
    max_budget_usd: str = ""
    escrow_eth: str = ""


def select_task(cycle_index: int, seed: int | None = None) -> TaskSpec:
    rng = random.Random(seed if seed is not None else cycle_index)
    t = rng.choice(TASK_TEMPLATES)
    budget = t["budget_class"]
    prices = PRICE_BY_BUDGET.get(budget, PRICE_BY_BUDGET["standard"])
    usd = float(prices["usd"])
    return TaskSpec(
        task_type=t["task_type"],
        complexity=t["complexity"],
        sla_seconds=t["sla_seconds"],
        budget_class=budget,
        template=t["template"],
        validation_rule=t["validation_rule"],
        quoted_price_xrp=prices["xrp"],
        quoted_price_usd=prices["usd"],
        max_budget_usd=f"{usd*1.5:.4f}",
        escrow_eth=prices.get("escrow_eth", "0.01"),
    )
