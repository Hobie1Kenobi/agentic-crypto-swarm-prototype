from typing import TypedDict, Optional


class SwarmState(TypedDict, total=False):
    goal: str
    tasks: list[str]
    ip_output: Optional[str]
    deploy_status: Optional[str]
    marketplace_summary: Optional[str]
    marketplace_done: bool
    marketplace_tx_hashes: list[str]
    public_adapter_summary: Optional[str]
    public_adapter_done: bool
    public_adapter_external_request_id: Optional[str]
    public_adapter_internal_task_id: Optional[int]
    public_adapter_tx_hashes: list[str]
    simulation_summary: Optional[str]
    treasury_balance_wei: Optional[int]
    profit_so_far_wei: Optional[int]
    tx_hashes: list[str]
    done: bool
