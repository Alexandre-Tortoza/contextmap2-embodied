# Technology Decisions

This document records the initial reuse-first technology choices for the first embodied validation product.

## Supported runtime

### Distrobox + Ubuntu 24.04

The host is Arch Linux. The supported robotics environment is an Ubuntu 24.04 Distrobox.

Distrobox is used because it shares the host user's home, networking, devices, and graphical sockets while allowing the ROS/Gazebo stack to stay on the Ubuntu platform expected by upstream packages.

References:

- https://distrobox.it/
- https://distrobox.it/usage/distrobox-assemble/
- https://distrobox.it/usage/distrobox-create/

The repository should version a `distrobox.ini` and use `distrobox assemble` as the canonical environment entry point.

## ROS and simulation

### ROS 2 Jazzy + Gazebo Harmonic

Use ROS 2 Jazzy on Ubuntu 24.04 with Gazebo Harmonic.

This is the supported/recommended pairing for the project baseline.

Reference:

- https://gazebosim.org/docs/harmonic/ros_installation/

### Nav2

Nav2 owns robot navigation. Do not implement a custom planner, controller, costmap, or low-level velocity controller for the initial product.

Use:

- `NavigateToPose` for resolved single targets;
- `NavigateThroughPoses` / waypoint following where appropriate;
- Nav2 Behavior Trees and recovery logic underneath the mission executor;
- occupancy/costmap information to validate approach poses.

References:

- https://docs.nav2.org/jazzy/getting_started/quickstart/quickstart/
- https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/bt_plugins/actions/NavigateToPose/
- https://docs.nav2.org/jazzy/getting_started/nav2_behavior_trees/

### Initial robot

Start with the maintained Nav2 minimal TurtleBot simulation rather than creating a robot model from scratch.

The first product is about ContextMap2 grounding and embodied execution, not robot dynamics.

Reference:

- https://docs.nav2.org/jazzy/getting_started/quickstart/quickstart/

## Natural-language agent

### Primary: RAI

Use RAI as the first integration target for natural-language interaction.

Reasons:

- explicit support for ROS 2 Jazzy;
- existing ROS 2 topic/service/action tools;
- existing Nav2-specific tools including `NavigateToPoseTool`;
- custom tools via LangChain `BaseTool` / `@tool`;
- access-control concepts for readable/writable/forbidden ROS resources;
- existing embodied-agent and benchmarking concepts.

References:

- https://robotecai.github.io/rai/
- https://robotecai.github.io/rai/tutorials/tools/
- https://robotecai.github.io/rai/API_documentation/langchain_integration/ROS_2_tools/

The agent must not use generic ROS write tools to publish `cmd_vel`. The normal product path is:

```text
natural language
  -> ContextMap tools / plan compiler
  -> validated MissionPlan
  -> deterministic MissionExecutor
  -> Nav2 action
```

### Alternative / experiment: ROS-MCP Server

ROS-MCP is a credible alternative when an MCP-native integration is specifically useful. It can expose ROS topics, services, and actions to MCP clients.

Reference:

- https://github.com/robotmcp/ros-mcp-server

It is not the primary dependency initially because maintaining both RAI and ROS-MCP would add unnecessary surface area. Re-evaluate only with a concrete measured benefit.

## Internal contracts

### Pydantic

Use Pydantic for:

- ContextMap query models;
- `MissionPlan`;
- target-resolution results;
- scenario definitions;
- execution/evaluation reports.

These models form the boundary between probabilistic language interpretation and deterministic execution.

## ContextMap2 integration

Do not create another map format or parse ContextMap2 storage files directly.

Use the public ContextMap2 artifact API, currently including:

- `ContextMapArtifactReader`;
- artifact validation/version information;
- map metadata and frame semantics;
- entity traversal;
- relation traversal;
- geometry references and geometry-source resolution.

The current artifact supports semantic entities and canonical graph predicates such as:

- `next_to`;
- `inside` / `contains`;
- `touching`;
- `above` / `below`;
- `in_front_of` / `behind`;
- `intersects`;
- `on_top_of`;
- `leaning_against`.

ContextMap2 source references:

- https://github.com/Alexandre-Tortoza/contextmap2/blob/dev/src/contextmap/artifact/__init__.py
- https://github.com/Alexandre-Tortoza/contextmap2/blob/dev/src/contextmap/artifact/serialization/reader.py
- https://github.com/Alexandre-Tortoza/contextmap2/blob/dev/src/contextmap/spatial_relations/taxonomy.py

## Explicitly rejected for the first product

Do not make the first release depend on:

- automatic Gazebo world reconstruction from the ContextMap point cloud;
- a custom LLM agent framework;
- custom SLAM;
- custom path planning;
- LLM-generated velocity commands;
- PX4/drone support;
- manipulation;
- a second ContextMap artifact schema.

These may become later experiments only after the ground-robot acceptance product is measured.
