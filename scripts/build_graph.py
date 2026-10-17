#!/usr/bin/env python3
"""Build docs/graph.json from graph/constellation.yaml.

What it does, in order:
  1. validates the authored graph (unique ids, known zones/kinds/statuses/relations,
     every edge endpoint exists, no self-loops, no orphans);
  2. turns repository / dataset / Space slugs into links (no URL is typed twice);
  3. computes analytics with networkx: degree (god nodes), bridges, components;
  4. writes docs/graph.json, which the page styles itself from. Layout is done
     client-side over the *revealed* subgraph, so modules always pack tightly.

    uv run python scripts/build_graph.py            # build
    uv run python scripts/build_graph.py --check    # validate only (CI-safe)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import networkx as nx
import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "graph" / "constellation.yaml"
OUT = ROOT / "docs" / "graph.json"

STATUSES = {"active", "pending", "retired"}

# kind → shape + box. Shape names are Cytoscape.js node shapes.
KINDS: dict[str, dict] = {
    "package": {"shape": "round-rectangle", "width": 168, "height": 46},
    "dataset": {"shape": "barrel", "width": 184, "height": 44},
    "model": {"shape": "round-diamond", "width": 184, "height": 52},
    "stage": {"shape": "ellipse", "width": 132, "height": 44},
    "aux": {"shape": "rhomboid", "width": 142, "height": 44},
    "service": {"shape": "hexagon", "width": 142, "height": 44},
    "script": {"shape": "tag", "width": 150, "height": 42},
    "doc": {"shape": "rectangle", "width": 162, "height": 44},
    "milestone": {"shape": "diamond", "width": 172, "height": 52},
    "external": {"shape": "diamond", "width": 150, "height": 48},
}


class GraphError(Exception):
    """The authored graph is not valid."""


def load() -> dict:
    data = yaml.safe_load(SOURCE.read_text())
    if not isinstance(data, dict):
        raise GraphError(f"{SOURCE} did not parse as a mapping")
    return data


def validate(data: dict) -> list[str]:
    """Raise on hard errors; return soft warnings."""
    warnings: list[str] = []
    zones = {z["id"]: z for z in data["zones"]}
    nodes = data["nodes"]
    relations = set(data["meta"]["relations"])

    if len({n["id"] for n in nodes}) != len(nodes):
        raise GraphError("duplicate node ids")

    for n in nodes:
        for key in ("id", "label", "zone", "kind", "status", "desc"):
            if not n.get(key):
                raise GraphError(f"node {n.get('id', '?')}: missing {key}")
        if n["zone"] not in zones:
            raise GraphError(f"node {n['id']}: unknown zone {n['zone']}")
        if n["kind"] not in KINDS:
            raise GraphError(f"node {n['id']}: unknown kind {n['kind']}")
        if n["status"] not in STATUSES:
            raise GraphError(f"node {n['id']}: unknown status {n['status']}")
        if len(n["desc"]) > 220:
            warnings.append(f"node {n['id']}: description is long ({len(n['desc'])} chars)")

    ids = {n["id"] for n in nodes}
    seeds = set(data["meta"].get("seeds") or [])
    unknown = seeds - ids
    if unknown:
        raise GraphError(f"meta.seeds names unknown nodes: {sorted(unknown)}")
    seen: set[tuple[str, str, str]] = set()
    for e in data["edges"]:
        src, dst, rel = e[0], e[1], e[2]
        if rel not in relations:
            raise GraphError(f"edge {src}->{dst}: unknown relation {rel}")
        if src not in ids or dst not in ids:
            raise GraphError(f"edge {src}->{dst}: endpoint is not a node")
        if src == dst:
            raise GraphError(f"self-loop on {src}")
        if (src, dst, rel) in seen:
            raise GraphError(f"duplicate edge {src}->{dst} ({rel})")
        seen.add((src, dst, rel))

    degree: dict[str, int] = {i: 0 for i in ids}
    for e in data["edges"]:
        degree[e[0]] += 1
        degree[e[1]] += 1
    for node_id, deg in degree.items():
        if deg == 0:
            warnings.append(f"orphan node: {node_id}")

    return warnings


def links_for(node: dict) -> list[dict]:
    """Repository / dataset / Space slugs → clickable links."""
    links: list[dict] = []
    repo = node.get("repo")
    if repo:
        links.append({"label": "repository", "url": f"https://github.com/{repo}"})
        if node.get("pages"):
            owner, name = repo.split("/", 1)
            host = {"Exios66": "exios66.github.io",
                    "LLM-Mailroom-Services": "llm-mailroom-services.github.io"}.get(owner)
            if host:
                links.append({"label": "GitHub Pages", "url": f"https://{host}/{name}/"})
    for field, label, base in (
        ("hf_dataset", "Hugging Face dataset", "https://huggingface.co/datasets/"),
        ("hf_space", "Hugging Face Space", "https://huggingface.co/spaces/"),
        ("hf_model", "Hugging Face model", "https://huggingface.co/"),
    ):
        if node.get(field):
            links.append({"label": label, "url": base + node[field]})
    if node.get("url"):
        links.append({"label": "live site", "url": node["url"]})
    return links


def analytics(data: dict) -> dict:
    g = nx.DiGraph()
    g.add_nodes_from(n["id"] for n in data["nodes"])
    g.add_edges_from((e[0], e[1]) for e in data["edges"])
    undirected = g.to_undirected()

    degree = dict(g.degree())
    by_zone = {z["id"]: 0 for z in data["zones"]}
    by_status = {s: 0 for s in sorted(STATUSES)}
    by_relation: dict[str, int] = {}
    for n in data["nodes"]:
        by_zone[n["zone"]] += 1
        by_status[n["status"]] += 1
    for e in data["edges"]:
        by_relation[e[2]] = by_relation.get(e[2], 0) + 1

    def brief(node_id: str) -> dict:
        node = next(n for n in data["nodes"] if n["id"] == node_id)
        return {
            "id": node_id,
            "label": node["label"],
            "zone": node["zone"],
            "degree": degree[node_id],
        }

    god = [brief(i) for i, _ in sorted(degree.items(), key=lambda kv: (-kv[1], kv[0]))[:8]]
    bridges = [
        (a, b) for a, b in nx.bridges(undirected) if "zone:" not in (a, b)
    ]
    bridge_brief = [
        {"from": a, "to": b, "weight": degree[a] + degree[b]}
        for a, b in sorted(bridges, key=lambda ab: -(degree[ab[0]] + degree[ab[1]]))[:8]
    ]
    components = sorted(nx.weakly_connected_components(g), key=len, reverse=True)

    return {
        "god_nodes": god,
        "bridges": bridge_brief,
        "components": len(components),
        "largest_component": len(components[0]) if components else 0,
        "zone_counts": by_zone,
        "status_counts": by_status,
        "relation_counts": by_relation,
    }


def build() -> dict:
    data = load()
    warnings = validate(data)
    stats = analytics(data)
    seeds = set(data["meta"].get("seeds") or [])

    zones = [
        {
            "id": z["id"],
            "label": z["label"],
            "blurb": z["blurb"],
            "fill": z["fill"],
            "border": z["border"],
            "count": stats["zone_counts"][z["id"]],
        }
        for z in data["zones"]
    ]

    nodes = []
    for n in data["nodes"]:
        zone = next(z for z in data["zones"] if z["id"] == n["zone"])
        kind = KINDS[n["kind"]]
        nodes.append(
            {
                "data": {
                    "id": n["id"],
                    "label": n["label"],
                    "zone": n["zone"],
                    "kind": n["kind"],
                    "status": n["status"],
                    "desc": n["desc"],
                    "version": n.get("version", ""),
                    "shape": kind["shape"],
                    "width": kind["width"],
                    "height": kind["height"],
                    "fill": zone["fill"],
                    "border": zone["border"],
                    "zoneLabel": zone["label"],
                    "col": n.get("col", 0),
                    "seed": n["id"] in seeds,
                    "links": links_for(n),
                },
            }
        )

    relations = data["meta"]["relations"]
    edges = [
        {
            "data": {
                "id": f"{e[0]}__{e[1]}__{e[2]}",
                "source": e[0],
                "target": e[1],
                "rel": e[2],
                "note": e[3] if len(e) > 3 else "",
                "color": RELATION_STYLE[e[2]]["color"],
                "line": RELATION_STYLE[e[2]]["line"],
            }
        }
        for e in data["edges"]
    ]

    return {
        "meta": {
            **data["meta"],
            "generated": date.today().isoformat(),
            "builder": "scripts/build_graph.py",
            "source": "graph/constellation.yaml",
            "counts": {
                "nodes": len(nodes),
                "edges": len(edges),
                "relations": len(RELATION_STYLE),
            },
        },
        "zones": zones,
        "kinds": KINDS,
        "relations": {
            rid: {**RELATION_STYLE[rid], "meaning": relations[rid]} for rid in RELATION_STYLE
        },
        "layout": data["layout"],
        "analytics": stats,
        "elements": {"nodes": nodes, "edges": edges},
    }


# Canvas styles live here because they pair a colour with a line style;
# everything else about a relation (its meaning) stays in the YAML.
RELATION_STYLE: dict[str, dict] = {
    "feeds": {"color": "#D9A03C", "line": "solid"},
    "produces": {"color": "#D9A03C", "line": "dashed"},
    "depends": {"color": "#7FA6C9", "line": "solid"},
    "traces": {"color": "#8E86E8", "line": "dashed"},
    "renders": {"color": "#E5808F", "line": "dashed"},
    "serves": {"color": "#4FC3B4", "line": "dotted"},
    "governs": {"color": "#B9C3CE", "line": "dotted"},
    # Cytoscape.js line styles are solid | dashed | dotted only.
    "syncs": {"color": "#B9C3CE", "line": "dashed"},
    "deploys": {"color": "#4FC3B4", "line": "dashed"},
    "supersedes": {"color": "#7B8494", "line": "dashed"},
    "prunes": {"color": "#C25A6A", "line": "dashed"},
    "documents": {"color": "#E5808F", "line": "dotted"},
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate only, write nothing")
    args = parser.parse_args()

    try:
        data = load()
        warnings = validate(data)
    except GraphError as exc:
        print(f"graph invalid: {exc}", file=sys.stderr)
        return 1
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if args.check:
        print(f"ok: {len(data['nodes'])} nodes, {len(data['edges'])} edges")
        return 0

    graph = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(graph, ensure_ascii=False, indent=1) + "\n")

    counts = graph["meta"]["counts"]
    stats = graph["analytics"]
    print(f"wrote {OUT.relative_to(ROOT)} — {counts['nodes']} nodes, {counts['edges']} edges")
    print(f"zones: {dict(stats['zone_counts'])}")
    print(f"status: {dict(stats['status_counts'])}")
    print("god nodes: " + ", ".join(f"{g['label']} ({g['degree']})" for g in stats["god_nodes"][:5]))
    print(f"components: {stats['components']} (largest {stats['largest_component']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
