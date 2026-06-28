# fab-plugins

A versioned Claude Code marketplace for fabian's custom skills — 69 skills
packaged into 5 short-namespaced plugins, git-tracked and version-pinned at
https://github.com/fabiantax/claude-plugins.

## Install

```bash
# 1. add the marketplace (do this once per machine)
/plugin marketplace add https://github.com/fabiantax/claude-plugins

# 2. install the plugins you want (short namespaces — fab, mesh, quant, strix, ml)
/plugin install fab@fab-plugins        # portable — daily-driver skills — install anywhere
/plugin install mesh@fab-plugins       # host-bound (A2A mesh + services) — opt-in
/plugin install quant@fab-plugins      # quant value stream
/plugin install strix@fab-plugins      # Strix box only (GPU/ROCm/llama.cpp) — opt-in
/plugin install ml@fab-plugins         # ML eval/bench/training
```

Plugin skills are **namespaced** — invoked as `<plugin>:<skill>`, e.g.
`fab:loopit`, `mesh:gitea`, `strix:llama-cpp-rocm`, `ml:code-bench`. They cannot
conflict with skills at other levels (per the Claude Code plugin spec).

## Plugins

| Plugin (namespace) | Portability | Skills | defaultEnabled |
|---|---|---|---|
| **`fab`** | portable | loopit (+`/loopit`), deliberate, prioritize, ship, plan-and-decompose, visual-plan, visual-recap, quick-recap, catch-up, handover, triz, creative-thinking, creative-thinking-ml, stay-within-limits, rust-decouple, preview, mermaid-local, loop-improvement, svelte-error-handling, svelte-performance, scrapling, emd-optimization | `true` |
| **`mesh`** | host-bound | fab-agent-runtime, fab-agent-add-mesh, fab-agent-add-peer, mesh-context, graphfusion, gitea, gitea-pm, gitea-bots, woodpecker, bifrost, tensorzero-gateway, openobserve | `false` |
| **`quant`** | portable-ish | fab-swarm-trading, indicator-creator, quant-consult, efficient-frontier, fable-efficient, cosmos-gl, casbin-ecosystem, pi-coding-agent, moshi-best-practices | `true` |
| **`strix`** | Strix box | llama-cpp-rocm, llama-cpp-vulkan, vllm, vllm-internals, model-runtime, rocm-profiling, rdna35-architecture, pytorch-rocm, hipblas-internals, triton-kernels, qwen36-architecture, container-ml-stack, toolbox-ml | `false` |
| **`ml`** | portable | model-guide, model-picker, model-quantization, code-bench, niah-bench, llm-eval-overview, thinking-eval, huggingface-workflow, gpu-bench-pipeline, mlflow-experiments, model-training, gepa, skillopt-rust-bugfix | `true` |

`defaultEnabled: false` means the plugin installs disabled — enable the ones you
need with `/plugin` after install, so a public install elsewhere doesn't pull in
host-specific paths.

## Versioning

- Each plugin carries an explicit `version` in its `plugin.json`.
- `marketplace.json` entries pin to a matching `version`.
- Reproducible installs are anchored to a git tag (`v0.2.0`); `ref` pins are
  added to the marketplace entries when a stable tag is cut.

### v0.2.0 — plugin rename (breaking identity change)

Plugins were renamed for a cleaner namespace prefix (the part you type):

| v0.1.0 | v0.2.0 |
|---|---|
| fab-coding-loop | **fab** |
| fab-mesh | **mesh** |
| fab-quant | **quant** |
| strix-machine | **strix** |
| fab-ml-lab | **ml** |

The marketplace name (`fab-plugins`) and skill contents are unchanged. **To
upgrade:** uninstall the old names, then install the new —
`claude plugin uninstall fab-coding-loop@fab-plugins` etc., then
`claude plugin install fab@fab-plugins` etc.

## Repository layout

```
.claude-plugin/marketplace.json        # the marketplace (lists all plugins)
plugins/
  <plugin>/                            # fab, mesh, quant, strix, ml
    .claude-plugin/plugin.json         # plugin manifest (strict mode)
    skills/<name>/SKILL.md             # + bundled assets (scripts/, references/)
    commands/loopit.md                 # (fab only)
```

## Coexistence with unversioned `~/.claude/skills/`

The unversioned copies in `~/.claude/skills/` and `~/.claude/commands/loopit.md`
are **intentionally kept** for now. Because plugin skills are namespaced
(`fab:loopit`) they do **not** shadow bare `/loopit` — the two coexist:

- bare `/loopit`, `/prioritize`, `/deliberate`, `/ship` → the unversioned copies
- `fab:loopit`, `fab:deliberate`, … → the versioned plugin copies

Retiring the unversioned copies later would change bare invocation to the
namespaced form everywhere, so it's deferred until explicitly wanted. Don't
retire without re-confirming.

The conversion + frontmatter normalization is reproducible via `build.py`
(reads `~/.claude/skills/` read-only, writes into `plugins/`).

## Rebuilding

```bash
python3 build.py   # re-copies + normalizes from ~/.claude/skills into plugins/
```

## Out of scope

Repo-level skills (`company-loop`, per-repo skills) stay versioned via their
own repos' git.

### speckit-* — removed (superseded by the upstream `specify` CLI)

A `speckit` plugin was added in v0.3.0 to dedupe the `speckit-*` skills vendored
across the mesh repos. It has been **removed** — those skills are now managed by
the upstream [`specify`](https://github.com/github/spec-kit) CLI, which already
provides version pinning, per-file manifest hashes, and diff-aware upgrades.
The plugin re-invented a mechanism upstream ships. The repos manage their
`speckit-*` skills directly via `.specify/` (GraphFusion, fab-trader,
localscout, atlas) or are migrated to it (fab-agent-mesh → `specify init`).

