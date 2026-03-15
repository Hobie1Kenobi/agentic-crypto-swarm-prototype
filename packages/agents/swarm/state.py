from typing import TypedDict, Optional


class SwarmState(TypedDict, total=False):
    goal: str
    tasks: list[str]
    ip_output: Optional[str]
    deploy_status: Optional[str]
    treasury_balance_wei: Optional[int]
    profit_so_far_wei: Optional[int]
    tx_hashes: list[str]
    done: bool
