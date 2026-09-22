# Development

The supported host is Arch Linux. ROS 2 and Gazebo are developed inside an Ubuntu 24.04 Distrobox.

## 1. Create the Distrobox

From the repository root on the Arch host:

```bash
distrobox assemble create --file distrobox.ini
distrobox enter contextmap2-embodied
```

## 2. Bootstrap Ubuntu, ROS 2, Gazebo, and Nav2

Inside the Distrobox:

```bash
cd ~/path/to/contextmap2-embodied
bash scripts/bootstrap-ubuntu.sh
source /opt/ros/jazzy/setup.bash
bash scripts/verify-env.sh
```

The bootstrap script is intended to be re-runnable. It does not modify the shared host shell startup files.

## 3. Create the Python development environment

Inside the Distrobox:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
make install-dev
make check
```

## Development boundary

The Python core must remain importable without ROS, Gazebo, or an LLM runtime. ROS, Nav2, RAI, and simulator integrations live behind adapters.

The first stable boundary is:

```text
natural language / agent
        |
        v
MissionPlan
        |
        v
deterministic query + execution
        |
        v
Nav2
```

An LLM must never be given a product path that publishes low-level velocity commands directly.

## Direct-to-main workflow

During the initial bootstrap phase this repository is developed directly on `main`. Each commit should remain small and correspond to one implementation issue or a clearly identified slice of one issue.

Before a commit is considered complete, run:

```bash
make check
```

Simulator work additionally needs its documented Gazebo/Nav2 integration smoke test.
