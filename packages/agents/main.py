#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

root = Path(__file__).resolve().parents[2]
for _ in range(5):
    if (root / "foundry.toml").exists() or (root / ".env.example").exists():
        break
    root = root.parent
load_dotenv(root / ".env")

from swarm.graph import get_compiled_graph


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal", default="maximize sustainable revenue via AI service")
    parser.add_argument("--max-steps", type=int, default=5)
    args = parser.parse_args()

    graph = get_compiled_graph()

    state = {"goal": args.goal, "tasks": [], "tx_hashes": []}
    step = 0

    last_state = state
    for event in graph.stream(state):
        step += 1
        for node, out in event.items():
            print(f"[{node}]", out)
            last_state = {**last_state, **out} if isinstance(out, dict) else last_state
        if step >= args.max_steps:
            print("Max steps reached.")
            break

    print("\n--- Final state ---")
    for k, v in last_state.items():
        if v is not None:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
