---
name: "Swarm Orchestration"
description: "Orchestrate multi-agent swarms with agentic-flow for parallel task execution, dynamic topology, and intelligent coordination. Use when scaling beyond single agents, implementing complex workflows, or building distributed AI systems. Triggers: swarm orchestration, multi-agent coordination, agent distribution, parallel execution, swarm topology, load balancing, task orchestration"
model: claude-sonnet-4-5-20250929
---

# Swarm Orchestration

## What This Skill Does

Orchestrates multi-agent swarms using agentic-flow's advanced coordination system. Supports mesh, hierarchical, and adaptive topologies with automatic task distribution, load balancing, and fault tolerance.

## When Claude Should Activate This Skill

Claude should automatically activate **swarm-orchestration** when:
- ✅ User mentions "swarm orchestration", "multi-agent coordination", or "agent swarm"
- ✅ User needs parallel execution: "run agents in parallel", "concurrent tasks"
- ✅ User requests topology setup: "mesh topology", "hierarchical swarm", "agent distribution"
- ✅ User wants load balancing: "distribute tasks", "balance workload across agents"
- ✅ User asks about scaling: "scale agents", "add more agents", "swarm scaling"
- ✅ User needs complex coordination: "coordinate multiple agents", "orchestrate workflow"

Claude should **NOT** activate this skill for:
- ❌ Single agent tasks (no coordination needed)
- ❌ Sequential workflows (no parallelism benefit)
- ❌ Simple automation scripts
- ❌ General programming questions

## Quick Start

```bash
# Initialize swarm
npx agentic-flow hooks swarm-init --topology mesh --max-agents 5

# Spawn agents
npx agentic-flow hooks agent-spawn --type coder
npx agentic-flow hooks agent-spawn --type tester
npx agentic-flow hooks agent-spawn --type reviewer

# Orchestrate task
npx agentic-flow hooks task-orchestrate \
  --task "Build REST API with tests" \
  --mode parallel
```

## Topology Patterns

### 1. Mesh (Peer-to-Peer)
```typescript
// Equal peers, distributed decision-making
await swarm.init({
  topology: 'mesh',
  agents: ['coder', 'tester', 'reviewer'],
  communication: 'broadcast'
});
```

### 2. Hierarchical (Queen-Worker)
```typescript
// Centralized coordination, specialized workers
await swarm.init({
  topology: 'hierarchical',
  queen: 'architect',
  workers: ['backend-dev', 'frontend-dev', 'db-designer']
});
```

### 3. Adaptive (Dynamic)
```typescript
// Automatically switches topology based on task
await swarm.init({
  topology: 'adaptive',
  optimization: 'task-complexity'
});
```

## Task Orchestration

### Parallel Execution
```typescript
// Execute tasks concurrently
const results = await swarm.execute({
  tasks: [
    { agent: 'coder', task: 'Implement API endpoints' },
    { agent: 'frontend', task: 'Build UI components' },
    { agent: 'tester', task: 'Write test suite' }
  ],
  mode: 'parallel',
  timeout: 300000 // 5 minutes
});
```

### Pipeline Execution
```typescript
// Sequential pipeline with dependencies
await swarm.pipeline([
  { stage: 'design', agent: 'architect' },
  { stage: 'implement', agent: 'coder', after: 'design' },
  { stage: 'test', agent: 'tester', after: 'implement' },
  { stage: 'review', agent: 'reviewer', after: 'test' }
]);
```

### Adaptive Execution
```typescript
// Let swarm decide execution strategy
await swarm.autoOrchestrate({
  goal: 'Build production-ready API',
  constraints: {
    maxTime: 3600,
    maxAgents: 8,
    quality: 'high'
  }
});
```

## Memory Coordination

```typescript
// Share state across swarm
await swarm.memory.store('api-schema', {
  endpoints: [...],
  models: [...]
});

// Agents read shared memory
const schema = await swarm.memory.retrieve('api-schema');
```

## Advanced Features

### Load Balancing
```typescript
// Automatic work distribution
await swarm.enableLoadBalancing({
  strategy: 'dynamic',
  metrics: ['cpu', 'memory', 'task-queue']
});
```

### Fault Tolerance
```typescript
// Handle agent failures
await swarm.setResiliency({
  retry: { maxAttempts: 3, backoff: 'exponential' },
  fallback: 'reassign-task'
});
```

### Performance Monitoring
```typescript
// Track swarm metrics
const metrics = await swarm.getMetrics();
// { throughput, latency, success_rate, agent_utilization }
```

## Integration with Hooks

```bash
# Pre-task coordination
npx agentic-flow hooks pre-task --description "Build API"

# Post-task synchronization
npx agentic-flow hooks post-task --task-id "task-123"

# Session restore
npx agentic-flow hooks session-restore --session-id "swarm-001"
```

## Best Practices

1. **Start small**: Begin with 2-3 agents, scale up
2. **Use memory**: Share context through swarm memory
3. **Monitor metrics**: Track performance and bottlenecks
4. **Enable hooks**: Automatic coordination and sync
5. **Set timeouts**: Prevent hung tasks

## Troubleshooting

### Issue: Agents not coordinating
**Solution**: Verify memory access and enable hooks

### Issue: Poor performance
**Solution**: Check topology (use adaptive) and enable load balancing

## Learn More

- Swarm Guide: docs/swarm/orchestration.md
- Topology Patterns: docs/swarm/topologies.md
- Hooks Integration: docs/hooks/coordination.md

## Version History

### v1.0.0 (2025-10-24)
- Initial creation with multi-agent swarm orchestration capabilities
- Support for mesh, hierarchical, and adaptive topologies
- Parallel, pipeline, and adaptive execution strategies
- Memory coordination for shared state
- Load balancing and fault tolerance
- Performance monitoring and metrics
- Integration with agentic-flow hooks system
