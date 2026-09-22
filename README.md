# contextmap2-embodied

Downstream validation project for [ContextMap2](https://github.com/Alexandre-Tortoza/contextmap2).

The product goal is to prove that a `ContextMapArtifact` can be consumed as an operational spatial memory by an embodied agent. A user gives a natural-language mission such as:

> Go to corridor X, then go to a place where there is a door next to a wooden pallet, then return to corridor X.

The system resolves semantic and spatial targets from the exported ContextMap2 artifact, compiles the instruction into a validated mission plan, and executes the plan with a simulated mobile robot in Gazebo through ROS 2 / Nav2.

## Scope

This repository owns the downstream integration:

```text
Natural language
      |
      v
Agent / structured planning
      |
      v
ContextMapArtifact queries
      |
      v
Validated MissionPlan
      |
      v
Nav2
      |
      v
Gazebo simulated robot
```

It does not own ContextMap2 perception, mapping, semantic fusion, entity resolution, or spatial-relation generation. Those remain in `contextmap2`.

## Baseline stack

- Host: Arch Linux
- Development environment: Distrobox with Ubuntu 24.04
- ROS: ROS 2 Jazzy
- Simulator: Gazebo Harmonic
- Navigation: Nav2
- Initial robot: differential-drive TurtleBot-compatible simulation
- Natural-language agent: RAI as the primary integration target
- Context map input: exported `ContextMapArtifact` / bundle from `contextmap2`
- Python: 3.12 inside the Jazzy environment

The LLM never publishes velocity commands. It produces or selects validated high-level actions. Robot motion remains deterministic and is executed through Nav2.

## Product acceptance scenario

The final acceptance scenario must support a mission equivalent to:

```text
Go to corridor X.
Then go to a place containing a door next to a wooden pallet.
Then return to corridor X.
```

The same mission must also support sequencing and repetition, for example:

```text
Go to the corridor containing three chairs, return to corridor B, and repeat this three times.
```

See [docs/PLAN.md](docs/PLAN.md) for architecture, milestones, metrics, and delivery criteria.
