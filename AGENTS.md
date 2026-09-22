# AGENTS.md

This repository is intended to be implemented primarily by coding agents. Treat the rules below as repository-level engineering constraints.

## Product boundary

`contextmap2-embodied` is a downstream consumer of the exported ContextMap2 artifact.

Do not move ContextMap2 perception, mapping, fusion, entity resolution, or spatial-relation logic into this repository.

Consume the public artifact contracts exposed by `contextmap2`, especially `ContextMapArtifactReader`, entities, relations, geometry references, metadata, frame declarations, and artifact validation.

## Architecture constraints

1. Natural language must never directly produce `cmd_vel`, wheel commands, Gazebo transport commands, or other low-level actuation.
2. Natural language is compiled to a typed, validated high-level mission representation.
3. Mission execution is deterministic once a `MissionPlan` has been accepted.
4. Nav2 owns path planning, collision avoidance, recovery, and path following.
5. Gazebo owns simulation physics.
6. The ContextMap2 artifact is authoritative for contextual semantics and relations. Do not silently replace missing artifact semantics with hand-written knowledge in production code.
7. Explicit test fixtures may contain synthetic or manually annotated semantics, but they must be labeled as fixtures.
8. Coordinate transforms between ContextMap2 and Gazebo / Nav2 frames must be explicit, validated, and testable.
9. Preserve uncertainty. A query must not silently choose an ambiguous entity when the artifact does not justify a unique choice.
10. Prefer existing libraries and ROS packages over custom implementations when a maintained implementation solves the requirement.

## Environment

Primary supported development path:

```text
Arch Linux host
  -> Distrobox
     -> Ubuntu 24.04
        -> ROS 2 Jazzy
        -> Gazebo Harmonic
        -> Nav2
```

Repository automation must not assume ROS or Gazebo packages are installed directly on the Arch host.

## Dependency policy

Preferred building blocks:

- ROS 2 Jazzy
- Gazebo Harmonic
- `ros_gz`
- Nav2
- Nav2 minimal TurtleBot simulation packages for initial bring-up
- RAI for natural-language / tool orchestration
- Pydantic for typed mission and query contracts
- ContextMap2 public artifact package/contracts

ROS-MCP may be evaluated as an alternative integration path, but do not maintain two agent stacks without measured justification.

## Development process

Every implementation issue must state:

1. Problem
2. Justification
3. Inputs
4. Processing
5. Outputs
6. Metrics / acceptance criteria
7. Tests

Branch naming:

```text
<type>/<issue-number>-<slug>
```

Keep changes scoped to one issue when possible.

Before opening a PR:

- run formatting and linting;
- run type checking;
- run unit tests;
- run relevant integration tests;
- record any simulator test that cannot run in CI and provide the exact local command.

## Testing principle

Do not treat a visually convincing Gazebo run as sufficient validation.

Separate at least:

- natural-language plan correctness;
- ContextMap query correctness;
- target entity correctness;
- target pose / frame transform correctness;
- Nav2 execution success;
- final goal error;
- sequence completion;
- repetition count;
- collisions / navigation failures.

Every failure should be attributable to one layer where practical.
