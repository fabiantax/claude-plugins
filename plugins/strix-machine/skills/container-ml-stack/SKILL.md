---
name: container-ml-stack
description: Container and toolbox management for ML workloads on Strix Halo. Covers podman, toolbox, vLLM container, and running ML code in isolated environments. Use when managing containers, building images, or setting up new ML environments.
allowed-tools: Read Bash
---

# Container ML Stack — Strix Halo

---

## Containers

| Container | Image | Purpose | Port |
|-----------|-------|---------|------|
| vllm-server | kyuz0/vllm-therock-gfx1151:20260422-075517 | vLLM inference | 8000 |
| strix-llama | kyuz0/amd-strix-halo-toolboxes:rocm-7.2.1 | ROCm toolchain (toolbox) | — |
| gitea | gitea/gitea:latest | Self-hosted Git | 3200 |
| open-webui | openwebui/open-webui:v0.8.12 | Chat UI | 3000 |
| lemonade | lemonade-sdk/lemonade-server:v10.2.0 | AMD Lemonade SDK | 8080 |

---

## Podman Commands

```bash
# List running containers
podman ps

# List all containers (including stopped)
podman ps -a

# Container logs
podman logs vllm-server --tail 50
podman logs -f vllm-server               # Follow

# Execute in running container
podman exec vllm-server python3 -c "..."
podman exec -it vllm-server bash          # Interactive shell

# Resource usage
podman stats --no-stream

# Stop/start
podman stop vllm-server
podman start vllm-server
```

---

## vLLM Container Details

### GPU Access

The container accesses the GPU via device passthrough:
```
--device /dev/kfd          # AMD Kernel Fusion Driver
--device /dev/dri          # Direct Rendering Infrastructure (GPU)
--group-add video          # Video device group
--group-add render         # Render device group
```

### Memory

```
--ipc=host                 # Shared memory for multiprocessing
--ulimit memlock=-1:-1     # Unlimited memory lock (GPU pinning)
--security-opt seccomp=unconfined  # Relaxed security for GPU compute
--cap-add SYS_PTRACE       # For profiling tools
```

### Network

The container uses pasta networking (rootless podman default):
- Binds to IPv4 only (IPv6 doesn't work with pasta)
- Always use `127.0.0.1` not `localhost` (to avoid IPv6 resolution)
- Port 8000 mapped: container → host

### Volumes Mounted

```bash
-v ~/models:/models:z                               # Model weights
-v ~/.config/vllm/patches/rocm.py:/opt/venv/.../rocm.py:z  # Patched ROCm platform
-v ~/.config/vllm/moe-configs/...:/opt/venv/.../configs/...:z  # MoE kernel config
```

---

## Toolbox (strix-llama)

Toolbox provides a persistent container environment with ROCm toolchain:

```bash
# Run command in toolbox
toolbox run -c strix-llama <command>

# Interactive shell
toolbox enter strix-llama

# Build llama.cpp
toolbox run -c strix-llama bash -c "cd ~/code/tools/llama.cpp && cmake --build build -j\$(nproc)"
```

### Toolbox vs Podman

| Feature | Toolbox | Podman |
|---------|---------|--------|
| Persistence | Yes (changes survive) | No (--rm removes on exit) |
| Home dir | Mounted | Only specified volumes |
| GPU access | Yes (automatic) | Manual device flags |
| Use for | Building binaries | Running services |

---

## Running ML Code in Container

### One-off Python Script

```bash
# Copy script to container, run it
podman cp script.py vllm-server:/tmp/script.py
podman exec vllm-server python3 /tmp/script.py

# Or pipe inline
podman exec -i vllm-server python3 << 'EOF'
import torch
print(torch.cuda.get_device_name(0))
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
EOF
```

### Interactive Python Session

```bash
podman exec -it vllm-server python3
```

### Jupyter (not installed but can add)

```bash
# Install Jupyter in container (survives until container restarts)
podman exec vllm-server pip install jupyterlab
podman exec -d vllm-server jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
# Access at http://127.0.0.1:8888
```

---

## Building Custom Images

```bash
# Build from Dockerfile
podman build -t my-ml-image -f Dockerfile .

# Tag and push
podman tag my-ml-image registry.example.com/my-ml-image:latest
podman push registry.example.com/my-ml-image:latest
```

---

## Disk Usage

```bash
# Container images
podman system df

# Clean up unused images
podman image prune

# Clean up everything
podman system prune -a
```

### Image Sizes

| Image | Size |
|-------|------|
| vllm-therock-gfx1151 | 30.5 GB |
| amd-strix-halo-toolboxes | 7.2 GB |
| open-webui | 4.8 GB |
| lemonade-server | 961 MB |
| python:3.13-slim | 125 MB |
| gitea | 174 MB |
