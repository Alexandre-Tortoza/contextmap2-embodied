# Implementation Plan

## Product hypothesis

A portable ContextMap2 artifact can act as an operational spatial memory for an external embodied agent. The agent can use natural language to express a contextual task, resolve targets from the artifact's entities and relations, and execute the resulting mission in Gazebo without running the ContextMap2 mapping pipeline.

## End-to-end target

```text
User instruction
   |
   v
RAI / LLM
   |
   v
MissionPlan (typed + validated)
   |
   +--> ContextMap query tools
   |       |
   |       v
   |   ContextMapArtifactReader
   |
   v
Resolved mission targets
   |
   v
MissionExecutor
   |
   v
Nav2 actions
   |
   v
Gazebo Harmonic
```

Example:

```text
"Go to corridor X, then go to a place where there is
a door next to a wooden pallet, then return to X."
```

must resolve through artifact semantics / graph relations rather than hard-coded Gazebo model names.

## Reuse-first decisions

- Distrobox provides a reproducible Ubuntu 24.04 environment on the Arch host.
- ROS 2 Jazzy + Gazebo Harmonic are the supported ROS / simulator pairing.
- Nav2 provides navigation, planners, controllers, costmaps, recovery, `NavigateToPose`, `NavigateThroughPoses`, waypoint following, and Behavior Tree execution.
- Nav2 minimal TurtleBot simulation is the initial mobile-robot baseline rather than implementing a robot stack.
- RAI is the primary natural-language agent candidate because it supports Jazzy, custom LangChain tools, ROS 2 tools, and Nav2-specific tools.
- Pydantic is used for internal typed contracts and validation.
- ContextMap2's own `ContextMapArtifactReader` and schema are used instead of implementing a second artifact parser.

## ContextMap2 assumptions verified against the current dev branch

The current ContextMap2 artifact already exposes:

- a portable, versioned `ContextMapArtifact`;
- explicit map metadata and coordinate-frame semantics;
- entities with geometry references and open-vocabulary semantic hypotheses;
- relations between entities;
- canonical spatial predicates including `next_to`, `inside`, `contains`, `touching`, `above`, `below`, `intersects`, `on_top_of`, and others;
- direct artifact traversal with `ContextMapArtifactReader`;
- geometry resolution through the referenced geometric-map artifact.

The embodied project must adapt to this contract, not invent a parallel map schema.

## Mission model

Natural language does not directly control the robot. It is compiled to a replayable intermediate representation.

Initial action vocabulary:

```text
ResolveTarget(query)
NavigateTo(target)
NavigateThrough(targets)
Sequence(actions)
Repeat(count, actions)
```

Initial query vocabulary:

```text
semantic(label)
entity_id(id)
relation(subject, predicate, object)
contains(container, semantic(label), count?)
next_to(a, b)
inside(a, b)
AND / OR constraints
```

The query layer may compute derived geometric facts such as distance when required, but it must distinguish derived query-time measurements from relations persisted in the artifact.

## Milestones

### M0 - Reproducible development environment

Deliver a Distrobox-based Ubuntu 24.04 environment with ROS 2 Jazzy, Gazebo Harmonic, Nav2, Python tooling, and repeatable smoke tests.

Exit criterion: a clean Arch host can create the distrobox and execute the documented simulator smoke test.

### M1 - Deterministic Gazebo / Nav2 baseline

Bring up a differential-drive robot in a controlled Gazebo world and navigate to explicit poses without ContextMap2 and without an LLM.

Exit criterion: scripted multi-goal navigation is repeatable and measurable.

### M2 - ContextMap artifact query and grounding

Load a real exported ContextMap2 artifact, validate compatibility, traverse semantic entities and graph relations, resolve geometry, align frames, and turn query results into navigable poses.

Exit criterion: a structured query can select an artifact entity / region and the robot can navigate to its derived target pose.

### M3 - Typed mission execution

Define a deterministic `MissionPlan` and execute sequence / repeat semantics through Nav2 with logging, failure handling, and replay.

Exit criterion: the acceptance mission can be executed from a hand-authored `MissionPlan` with no LLM involved.

### M4 - Natural-language agent

Integrate RAI and expose only safe high-level ContextMap / mission tools. Compile free-form language into the same validated `MissionPlan` used by M3.

Exit criterion: multiple paraphrases of the acceptance instruction produce valid plans and execute successfully without low-level LLM actuation.

### M5 - Evaluation and product acceptance

Create reproducible scenarios and quantitative reports covering grounding, graph queries, navigation, sequencing, repetitions, failures, and final goal error.

Exit criterion: the documented end-to-end acceptance scenarios pass from clean environment setup through Gazebo execution.

## Delivery issue map

The GitHub backlog is organized in dependency order:

- M0 tracker #22: #1, #2, #3
- M1 tracker #23: #4, #5, #6
- M2 tracker #24: #7, #8, #9, #10, #11
- M3 tracker #25: #12, #13, #14
- M4 tracker #26: #15, #16, #17, #18
- M5 tracker #27: #19, #20, #21

Recommended implementation order is the numeric issue order inside each milestone. Parallel work is acceptable only when issue inputs are already stable.

## Acceptance metrics

At minimum record:

- plan schema validity;
- intended target entity vs selected entity;
- relation / graph-query correctness;
- target pose validity;
- ContextMap-to-Nav2 frame transform error;
- Nav2 action success / failure;
- final Euclidean error to target;
- sequence completion ratio;
- requested vs completed repetitions;
- collision / recovery count where available;
- wall-clock and simulation time.

## Non-goals for the first product

- generating the Gazebo world automatically from the ContextMap point cloud;
- training semantic models;
- changing ContextMap2's mapping pipeline;
- custom SLAM;
- custom planners or controllers;
- drone / PX4 support;
- manipulation;
- direct velocity control by an LLM;
- hiding ambiguity in the artifact.

## Final acceptance scenario

The world and artifact fixture must contain at least:

- a named or semantically identifiable corridor X;
- a second navigable region;
- one door entity;
- one wooden-pallet entity;
- a supported `next_to` relation between the relevant door and pallet;
- sufficient geometry to derive a safe navigation goal near the selected target.

The final demo must accept an instruction equivalent to:

```text
Go to corridor X, then go to a place where there is a door
next to a wooden pallet, then return to corridor X.
```

and an instruction with repetition equivalent to:

```text
Go to the corridor containing three chairs, return to corridor B,
and repeat this three times.
```

The agent must resolve targets using the ContextMap2 artifact, not direct knowledge of Gazebo object names.
