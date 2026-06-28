#!/usr/bin/env python3
"""Build the claude-plugins marketplace from ~/.claude/skills (read-only on src).

For each skill: copy into its plugin's skills/<name>/ as SKILL.md, preserving any
bundled assets (scripts/, references/, gepa/, ...). Normalize the skill-file name
to SKILL.md (handles lowercase skill.md, README.md-only, and loose .md files).
Inject name:+description: frontmatter where missing.
"""
import os, re, shutil, sys

SRC = "/home/fabian/.claude/skills"
REPO = "/home/fabian/Developer/personal/claude-plugins"

# Directories/files never copied from a source skill dir (runtime cruft, build
# artifacts, or stale normalized-name dupes — SKILL.md is the canonical name).
JUNK_NAMES = (".venv", "venv", "__pycache__", ".cache")


def junk_ignore(directory, names):
    """shutil.copytree ignore-pattern: drop junk at every depth (so nested
    e.g. deliberate/gepa/__pycache__ is pruned, not just top-level)."""
    return [n for n in names
            if n in JUNK_NAMES or n.endswith(".bak") or ".bak-" in n]

ALLOCATION = {
    "fab": ["loopit","deliberate","prioritize","ship","plan-and-decompose","visual-plan","visual-recap","quick-recap","catch-up","handover","triz","creative-thinking","creative-thinking-ml","stay-within-limits","rust-decouple","preview","mermaid-local","loop-improvement","svelte-error-handling","svelte-performance","scrapling","emd-optimization"],
    "mesh": ["fab-agent-runtime","fab-agent-add-mesh","fab-agent-add-peer","mesh-context","graphfusion","gitea","gitea-pm","gitea-bots","woodpecker","bifrost","tensorzero-gateway","openobserve"],
    "quant": ["fab-swarm-trading","indicator-creator","quant-consult","efficient-frontier","fable-efficient","cosmos-gl","casbin-ecosystem","pi-coding-agent","moshi-best-practices"],
    "strix": ["llama-cpp-rocm","llama-cpp-vulkan","vllm","vllm-internals","model-runtime","rocm-profiling","rdna35-architecture","pytorch-rocm","hipblas-internals","triton-kernels","qwen36-architecture","container-ml-stack","toolbox-ml"],
    "ml": ["model-guide","model-picker","model-quantization","code-bench","niah-bench","llm-eval-overview","thinking-eval","huggingface-workflow","gpu-bench-pipeline","mlflow-experiments","model-training","gepa","skillopt-rust-bugfix"],
}

def slugify(name):
    return re.sub(r'[^a-z0-9-]', '-', name.lower()).strip('-') or name

def find_skill_file(skill_dir):
    """Return the path to the skill markdown file inside a skill dir, or None."""
    for cand in ("SKILL.md", "skill.md"):
        p = os.path.join(skill_dir, cand)
        if os.path.isfile(p):
            return p
    # fallback: any single .md
    mds = [f for f in os.listdir(skill_dir) if f.lower().endswith('.md') and os.path.isfile(os.path.join(skill_dir, f))]
    if len(mds) == 1:
        return os.path.join(skill_dir, mds[0])
    if mds:
        # prefer README.md
        for m in mds:
            if m.lower() == 'readme.md':
                return os.path.join(skill_dir, m)
    return None

def has_name_frontmatter(text):
    head = text.lstrip()
    if not head.startswith('---'):
        return False
    parts = head.split('---', 2)
    if len(parts) < 3:
        return False
    fm = parts[1]
    return bool(re.search(r'^name:\s*\S', fm, re.M))

def derive_description(text):
    """Pull a one-line description from the first meaningful line."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for l in lines:
        l = re.sub(r'^#+\s*', '', l)  # strip markdown heading
        if l and not l.startswith('---') and not l.startswith('name:') and not l.startswith('description:'):
            # trim to ~90 chars at word boundary
            if len(l) > 90:
                l = l[:90].rsplit(' ', 1)[0] + '…'
            return l
    return "fab skill"

def inject_frontmatter(name, text):
    """Ensure text has --- name: ... description: ... --- frontmatter."""
    if has_name_frontmatter(text):
        return text  # already has name:
    stripped = text.lstrip()
    desc = derive_description(text)
    fm = f"---\nname: {slugify(name)}\ndescription: {desc}\n---\n\n"
    if stripped.startswith('---'):
        # has a frontmatter block but no name: — inject into it
        parts = stripped.split('---', 2)
        if len(parts) >= 3:
            existing = parts[1]
            # if description exists but name doesn't, add name at top of fm
            if re.search(r'^description:', existing, re.M) and not re.search(r'^name:', existing, re.M):
                new_fm = f"\nname: {slugify(name)}\n" + existing.lstrip('\n')
                return f"---{new_fm}---" + parts[2]
            return f"---\nname: {slugify(name)}\ndescription: {desc}\n{existing}---" + parts[2]
    return fm + text

copied = 0
fm_added = 0
errors = []

for plugin, skills in ALLOCATION.items():
    plug_skills_dir = os.path.join(REPO, "plugins", plugin, "skills")
    for skill in skills:
        src_dir = os.path.join(SRC, skill)
        src_loose = os.path.join(SRC, skill + ".md")
        dst_dir = os.path.join(plug_skills_dir, skill)
        # clean dst first so re-runs don't leave stale dupes (e.g. a source's
        # lowercase skill.md / README.md after normalization to SKILL.md).
        if os.path.isdir(dst_dir):
            shutil.rmtree(dst_dir)
        os.makedirs(dst_dir, exist_ok=True)

        if os.path.isdir(src_dir):
            # copy whole dir (preserves assets), then normalize skill file name
            for entry in os.listdir(src_dir):
                if entry in JUNK_NAMES or entry.endswith(".bak") or ".bak-" in entry:
                    continue
                s = os.path.join(src_dir, entry)
                d = os.path.join(dst_dir, entry)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True, ignore=junk_ignore)
                else:
                    shutil.copy2(s, d)
            skill_file = find_skill_file(dst_dir)
            if skill_file is None:
                errors.append(f"{skill}: no skill file found after copy")
                continue
            # normalize name to SKILL.md
            target = os.path.join(dst_dir, "SKILL.md")
            if os.path.abspath(skill_file) != os.path.abspath(target):
                if os.path.exists(target):
                    os.remove(target)
                shutil.move(skill_file, target)
                skill_file = target
        elif os.path.isfile(src_loose):
            # loose .md -> SKILL.md in new dir
            target = os.path.join(dst_dir, "SKILL.md")
            shutil.copy2(src_loose, target)
            skill_file = target
        else:
            errors.append(f"{skill}: source not found ({src_dir} / {src_loose})")
            continue

        # frontmatter injection
        with open(skill_file, encoding='utf-8') as f:
            text = f.read()
        if not has_name_frontmatter(text):
            new_text = inject_frontmatter(skill, text)
            with open(skill_file, 'w', encoding='utf-8') as f:
                f.write(new_text)
            fm_added += 1
        copied += 1

# copy the loopit command
loopit_cmd_src = "/home/fabian/.claude/commands/loopit.md"
loopit_cmd_dst = os.path.join(REPO, "plugins", "fab", "commands", "loopit.md")
if os.path.isfile(loopit_cmd_src):
    shutil.copy2(loopit_cmd_src, loopit_cmd_dst)
    print(f"copied command: loopit.md")

print(f"\nCopied {copied} skills, added frontmatter to {fm_added}.")
if errors:
    print("ERRORS:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
print("No errors.")
