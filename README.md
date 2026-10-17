<div align="center">

# 🗺️ DMR-Graph

**Interactive knowledge graph of the Mailroom constellation — the pruned Digital-Mailroom monorepo (`v0.8.0` + DMR-079), its seven packages, the `LLM-Mailroom-Services` repos, and every pinned Hugging Face dataset and model.**

[![Live site](https://img.shields.io/badge/live%20site-exios66.github.io%2FDMR--Graph-blue)](https://exios66.github.io/DMR-Graph/)
[![Hub](https://img.shields.io/badge/hub-v0.8.0-4FC3B4)](https://github.com/LLM-Mailroom-Services/Digital-Mailroom)
[![Prune](https://img.shields.io/badge/prune-DMR--079-C25A6A)](https://github.com/LLM-Mailroom-Services/Digital-Mailroom)
[![Stack](https://img.shields.io/badge/networkx%20%2B%20Cytoscape.js-open%20source-6C63FF)](docs/vendor/README.md)
[![Pages](https://img.shields.io/badge/GitHub%20Pages-branch%20deploy%2C%20no%20Actions-2E7D32)](#deploy)

</div>

---

## What this is

One page that answers "how does the Digital Mailroom actually fit together?" — which
repository feeds which, what the pipeline's thirteen LangGraph nodes are, where the
scoring definition lives, which Hugging Face datasets everything pins, and what the
DMR-079 prune removed.

It is a **curated architecture graph**, not an AST dump: 128 nodes and 237 typed edges,
authored in [`graph/constellation.yaml`](graph/constellation.yaml) and validated,
laid out and analysed by [`scripts/build_graph.py`](scripts/build_graph.py)
(networkx) before being rendered by Cytoscape.js.

Every fact carries a source. The graph was assembled from the hub's own canonical map
(`packages/llm-mailroom/docs/constellation/*`, `README.md`, `docs/wiki/*`), the
`v0.8.0` rollback tag, the standalone repo READMEs, and the public Hugging Face API —
then re-verified by four independent research passes (2026-10-16). Where the wiki and
the code disagree (the wiki still describes a removed `after_intake` skip), the code wins
and the discrepancy is noted on the node.

## How to read the map

**Modules (colour = complementary pair).** The six zones are layout columns, left to right
along the flow of work. Each of the first three pairs sits opposite its partner on the wheel:

| Module | Colour | What lives there |
| :--- | :--- | :--- |
| **Data & corpora** | amber `#B87F26` | raw corpora, the three corpus-feed packages, every pinned HF dataset, and the external claim/merger corpora the canonical dataset is built from |
| **Evaluation & prompts** | indigo `#5A52C7` | the single scoring definition, per-node evals + calibration, the ModernBERT classifier and its published model bundle, the frozen v1 prompt lineage and the GEPA loop |
| **Pipeline & runtime** | teal `#0F8C7E` | llm-mailroom's 13 nodes, the auxiliary flows, persistence, `mailroom-reloaded`, the sandbox |
| **Surfaces** | rose `#C2465A` | console, Observatory, TUI, terminal site, boards, and the graph-site lineage |
| **Hub, governance & release** | steel `#3E6E9E` | the monorepo, its board, the ten gate scripts, the issue hub and the release milestones |
| **External platforms** | graphite `#5A6473` | providers, tracing sinks, GPU hosts, storage and hosting |

**Node kinds (shape).** `package` round-rectangle · `dataset` barrel · `model`
round-diamond · `stage` ellipse · `aux` rhomboid · `service` hexagon · `script` tag ·
`doc` rectangle · `milestone` diamond · `external` diamond.

**Status.** `active` solid border · `pending` dotted border · `retired` dashed border and
desaturated — the retired nodes are `llm-entity-extraction`, its org copy,
`llm-mailroom-graph`, `mailroom-dev-graph`, `agent-mailroom`, `agent-mailroom`'s office
floor and the earlier monorepos. `Hub v0.8.0` is the rollback point that still contained
all ten packages; `DMR-079` is the prune that removed three of them.

**Relations.** `feeds` (data/control flow) · `produces` · `depends` (pins, vendored
snapshots, imports) · `traces` · `renders` · `serves` · `governs` · `syncs` (mirror, fork,
upload) · `deploys` · `supersedes` · `prunes` · `documents` (this graph's own coverage).
Edge labels appear on hover and on selection; the sidebar isolates a relation.

**Interactions.** The map **starts folded** — only a small set of hub nodes is visible, and
you expand it as you explore: **double-click a node** to reveal its neighbours, click a
**module** row in the sidebar to reveal (or collapse) a whole zone, or **search** — matches
reveal themselves. `Expand all` shows everything at once. Drag to pan, scroll to zoom, click
a node for its description, version, links and neighbourhood (hidden neighbours are marked and
revealed on click). The sidebar also isolates relations and hides retired nodes; `PNG` exports
the current view; deep links look like `#node=mailroom-dataset`, and `?expand=all` shows the
whole map.

## Repository layout

```
dmr-graph/
├── graph/constellation.yaml      # the authored graph: zones, nodes, typed edges, sources
├── scripts/build_graph.py        # validate → link slugs → networkx analytics → docs/graph.json
├── scripts/deploy_gh_pages.py    # local Pages publish (orphan gh-pages push), no GitHub Actions
├── docs/                         # the published site
│   ├── index.html                # the explorer (data-driven styles; reads graph.json)
│   ├── graph.json                # generated — never hand-edit
│   └── vendor/cytoscape.min.js   # pinned Cytoscape.js (MIT) + provenance
└── pyproject.toml                # uv project: networkx, pyyaml
```

## Rebuild

```bash
uv run python scripts/build_graph.py           # writes docs/graph.json
uv run python scripts/build_graph.py --check   # validate only (fails on bad ids, unknown zones/kinds/relations, orphans)
```

The builder emits structure, not positions: the page packs the **revealed** subgraph into
zone columns client-side (zones are sized to their content, `col` selects a sub-column, and
`y_step` the row pitch), so modules never overlap whatever is unfolded. Analytics (god nodes,
bridges, components, counts) are computed by networkx at build time and shown in the sidebar.

## Deploy

GitHub Pages, served from the `gh-pages` branch, published **without GitHub Actions** —
the same house pattern as Digital-Mailroom's `scripts/deploy_gh_pages.py`:

```bash
uv run python scripts/deploy_gh_pages.py --repo Exios66/DMR-Graph            # build, create/push repo, publish site, enable Pages
uv run python scripts/deploy_gh_pages.py --repo Exios66/DMR-Graph --site-only
```

The published branch contains only `docs/`. To preview locally:

```bash
python3 -m http.server -d docs 8787   # then open http://127.0.0.1:8787/
```

## Adding to the graph

Add a node to `graph/constellation.yaml` — `id`, `label`, `zone`, `kind`, `status`,
`desc`, plus any of `repo`, `pages`, `hf_dataset`, `hf_model`, `hf_space`, `url`
(the build script turns slugs into links, so never paste a URL twice) — then an edge as
`[from, to, relation]` with an optional note. Rebuild; validation will tell you if an
endpoint, zone, kind or relation does not exist.

## Provenance

| Fact base | Source |
| :--- | :--- |
| Pruned constellation (7 packages) | `LLM-Mailroom-Services/Digital-Mailroom` @ `origin/main`, DMR-079 (`0ac7e4bc`, close-out `e8558a68`) |
| Pre-prune rollback point (10 packages) | hub tag `v0.8.0` (`5a2900c5`, annotated `dbc79ca3`) |
| Canonical written map | `packages/llm-mailroom/docs/constellation/{repo-index,architecture,overview,data-and-corpora}.md` |
| Pipeline internals | `packages/llm-mailroom/src/graph/build_graph.py`, `src/pipeline/*`, `src/llm/*`, `src/agents/*` |
| Org repos | `LLM-Mailroom-Services/{eval-environment,mailroom-ml,mailroom-issues}`, `Exios66/mailroom-reloaded` |
| Datasets, model, Spaces | public Hugging Face API (`Lucius-Morningstar` + the external feeder corpora) |
| Verification | four independent research passes, 2026-10-16; corrections applied to the YAML |

Vendored third-party code: Cytoscape.js (MIT) — see
[`docs/vendor/README.md`](docs/vendor/README.md).

<div align="center"><sub>Built by the governed evaluation family under
<a href="https://github.com/Exios66">@Exios66</a> · 2026 · the code is the truth</sub></div>
