#!/usr/bin/env bash
set -euo pipefail

if [[ ! -r /etc/os-release ]]; then
  echo "cannot determine operating system" >&2
  exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release

if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
  echo "expected Ubuntu 24.04 inside Distrobox, got ${PRETTY_NAME:-unknown}" >&2
  exit 1
fi

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates \
  curl \
  git \
  gnupg \
  locales \
  lsb-release \
  python3-pip \
  python3-venv \
  software-properties-common

sudo add-apt-repository universe -y

sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

sudo install -d -m 0755 /usr/share/keyrings
curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  | sudo tee /usr/share/keyrings/ros-archive-keyring.asc >/dev/null

architecture="$(dpkg --print-architecture)"
codename="${UBUNTU_CODENAME:-noble}"

echo "deb [arch=${architecture} signed-by=/usr/share/keyrings/ros-archive-keyring.asc] http://packages.ros.org/ros2/ubuntu ${codename} main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-vcstool \
  ros-dev-tools \
  ros-jazzy-desktop \
  ros-jazzy-navigation2 \
  ros-jazzy-nav2-bringup \
  ros-jazzy-ros-gz

if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init
fi

rosdep update

echo
echo "Bootstrap complete."
echo "For each shell, source ROS with:"
echo "  source /opt/ros/jazzy/setup.bash"
echo
echo "Then verify the environment with:"
echo "  ./scripts/verify-env.sh"
