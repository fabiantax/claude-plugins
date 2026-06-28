# fab-plugins

A versioned Claude Code marketplace for fabian's custom skills — replacing the
unversioned `~/.claude/skills/` copies with git-tracked, version-pinned plugins.

## Install

```bash
# 1. add the marketplace (do this once per machine)
/plugin marketplace add https://github.com/fabiantax/claude-plugins

# 2. install the plugins you want
/plugin install fab-coding-loop@fab-plugins   # portable — install anywhere
/plugin install fab-mesh@fab-plugins          # host-bound (A2A mesh + services) — opt-in
/plugin install fab-quant@fab-plugins         # quant value stream
/plugin install strix-machine@fab-plugins     # Strix box only (GPU/ROCm/llama.cpp) — opt-in
/plugin install fab-ml-lab@fab-plugins        # ML eval/bench/training
```

Installed skills live under `~/.claude/plugins/data/<plugin>-fab-plugins/`. The
unversioned `~/.claude/skills/<name>` copies are retired once the plugin versions
are confirmed working (see *Migration* below).

## Plugins

| Plugin | Portability | Skills | defaultEnabled |
|---|---|---|---|
| **fab-coding-loop** | portable | loopit (+`/loopit`), deliberate, prioritize, ship, plan-and-decompose, visual-plan, visual-recap, quick-recap, catch-up, handover, triz, creative-thinking, creative-thinking-ml, stay-within-limits, rust-decouple, preview, mermaid-local, loop-improvement, svelte-error-handling, svelte-performance, scrapling, emd-optimization | `true` |
| **fab-mesh** | host-bound | fab-agent-runtime, fab-agent-add-mesh, fab-agent-add-peer, mesh-context, graphfusion, gitea, gitea-pm, gitea-bots, woodpecker, bifrost, tensorzero-gateway, openobserve | `false` |
| **fab-quant** | portable-ish | fab-swarm-trading, indicator-creator, quant-consult, efficient-frontier, fable-efficient, cosmos-gl, casbin-ecosystem, pi-coding-agent, moshi-best-practices | `true` |
| **strix-machine** | Strix box | llama-cpp-rocm, llama-cpp-vulkan, vllm, vllm-internals, model-runtime, rocm-profiling, rdna35-architecture, pytorch-rocm, hipblas-internals, triton-kernels, qwen36-architecture, container-ml-stack, toolbox-ml | `false` |
| **fab-ml-lab** | portable | model-guide, model-picker, model-quantization, code-bench, niah-bench, llm-eval-overview, thinking-eval, huggingface-workflow, gpu-bench-pipeline, mlflow-experiments, model-training, gepa, skillopt-rust-bugfix | `true` |

`defaultEnabled: false` means the plugin installs disabled — enable the ones you
need with `/plugin` after install, so a public install elsewhere doesn't pull in
host-specific paths.

## Versioning

- Each plugin carries an explicit `version` in its `plugin.json`.
- `marketplace.json` entries pin to a matching `version`.
- Reproducible installs are anchored to a git tag (`v0.1.0`); `ref` pins are
  added to the marketplace entries when a stable tag is cut.

## Repository layout

```
.claude-plugin/marketplace.json        # the marketplace (lists all plugins)
plugins/
  <plugin>/
    .claude-plugin/plugin.json         # plugin manifest (strict mode)
    skills/<name>/SKILL.md             # + bundled assets (scripts/, references/)
    commands/loopit.md                 # (fab-coding-loop only)
```

## Migration (from unversioned `~/.claude/skills/`)

The unversioned copies must be **retired** after the plugin copies are confirmed
working — otherwise a same-name user-level skill shadows the plugin copy (this
bit us before with `loopit`). Procedure:

1. Install the plugins (above) and confirm they load (`/plugin list`,
   `/plugin details <name>`, and a functional spot-check in a fresh session).
2. Move — do not `rm` — the matched `~/.claude/skills/<name>` dirs into
   `~/.claude/skills.bak-unversioned/`, and move `~/.claude/commands/loopit.md`
   aside too.
3. Keep the backup for one full session; delete once confirmed stable.

The conversion + frontmatter normalization is reproducible via `build.py`
(reads `~/.claude/skills/` read-only, writes into `plugins/`).

## Rebuilding

```bash
python3 build.py   # re-copies + normalizes from ~/.claude/skills into plugins/
```

## Out of scope

Repo-level skills (`company-loop`, `speckit-*`, per-repo skills) stay versioned
via their own repos' git. Cross-repo drift of those copies is a separate,
follow-on cleanup once this marketplace exists.
