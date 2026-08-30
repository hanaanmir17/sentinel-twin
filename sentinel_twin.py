from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


@dataclass(frozen=True)
class Node:
    name: str
    kind: str
    criticality: int = 1


class DigitalTwin:
    def __init__(self, nodes: Dict[str, Node], links: List[dict], roots: Iterable[str]):
        self.nodes = nodes
        self.links = links
        self.roots = list(roots)

    @classmethod
    def from_file(cls, path: str) -> "DigitalTwin":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        nodes = {
            item["id"]: Node(
                name=item.get("name", item["id"]),
                kind=item.get("type", "unknown"),
                criticality=int(item.get("criticality", 1)),
            )
            for item in data["nodes"]
        }
        return cls(nodes, data.get("links", []), data.get("roots", []))

    def adjacency(
        self,
        failed_devices: Set[str] | None = None,
        failed_links: Set[Tuple[str, str]] | None = None,
    ) -> Dict[str, List[str]]:
        failed_devices = failed_devices or set()
        failed_links = failed_links or set()
        graph = {node_id: [] for node_id in self.nodes if node_id not in failed_devices}

        for link in self.links:
            src, dst = link["from"], link["to"]
            if src in failed_devices or dst in failed_devices:
                continue
            if (src, dst) in failed_links:
                continue
            graph.setdefault(src, []).append(dst)
            if link.get("bidirectional", True):
                if (dst, src) not in failed_links:
                    graph.setdefault(dst, []).append(src)
        return graph

    def reachable(
        self,
        failed_devices: Set[str] | None = None,
        failed_links: Set[Tuple[str, str]] | None = None,
    ) -> Set[str]:
        graph = self.adjacency(failed_devices, failed_links)
        failed_devices = failed_devices or set()
        queue = deque(root for root in self.roots if root in graph and root not in failed_devices)
        seen = set(queue)

        while queue:
            current = queue.popleft()
            for neighbor in graph.get(current, []):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        return seen

    def simulate(
        self,
        failed_devices: Set[str] | None = None,
        failed_links: Set[Tuple[str, str]] | None = None,
    ) -> dict:
        failed_devices = failed_devices or set()
        reachable = self.reachable(failed_devices, failed_links)
        impacted = sorted(set(self.nodes) - reachable - failed_devices)
        failed = sorted(failed_devices)
        blast_score = sum(self.nodes[node].criticality for node in impacted + failed)

        return {
            "failed_devices": failed,
            "unreachable_devices": impacted,
            "reachable_devices": sorted(reachable),
            "blast_radius_score": blast_score,
        }


def parse_link(value: str) -> Tuple[str, str]:
    try:
        src, dst = value.split(":", 1)
        return src, dst
    except ValueError as exc:
        raise argparse.ArgumentTypeError("link must look like source:destination") from exc


def print_report(result: dict) -> None:
    print("\n=== Sentinel Twin Incident Simulation ===")
    print(f"Blast radius score: {result['blast_radius_score']}")
    print("Failed devices:", ", ".join(result["failed_devices"]) or "none")
    print("Unreachable:", ", ".join(result["unreachable_devices"]) or "none")
    print("Still reachable:", ", ".join(result["reachable_devices"]) or "none")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate defensive network failures from a topology file.")
    parser.add_argument("topology")
    parser.add_argument("--fail-device", action="append", default=[])
    parser.add_argument("--fail-link", action="append", type=parse_link, default=[])
    args = parser.parse_args()

    twin = DigitalTwin.from_file(args.topology)
    unknown = set(args.fail_device) - set(twin.nodes)
    if unknown:
        raise SystemExit(f"Unknown device(s): {', '.join(sorted(unknown))}")

    result = twin.simulate(set(args.fail_device), set(args.fail_link))
    print_report(result)


if __name__ == "__main__":
    main()
