#!/usr/bin/env bash
set -euo pipefail

failures=0

check_command() {
  local command_name="$1"
  if command -v "$command_name" >/dev/null 2>&1; then
    printf "ok   command: %s\n" "$command_name"
  else
    printf "FAIL command: %s\n" "$command_name" >&2
    failures=$((failures + 1))
  fi
}

check_ros_package() {
  local package_name="$1"
  if ros2 pkg prefix "$package_name" >/dev/null 2>&1; then
    printf "ok   ROS package: %s\n" "$package_name"
  else
    printf "FAIL ROS package: %s\n" "$package_name" >&2
    failures=$((failures + 1))
  fi
}

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  printf "os: %s\n" "${PRETTY_NAME:-unknown}"
  if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
    printf "FAIL expected Ubuntu 24.04\n" >&2
    failures=$((failures + 1))
  fi
fi

if [[ -f /opt/ros/jazzy/setup.bash ]]; then
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
  printf "ok   ROS setup: /opt/ros/jazzy/setup.bash\n"
else
  printf "FAIL ROS setup: /opt/ros/jazzy/setup.bash\n" >&2
  failures=$((failures + 1))
fi

check_command python3
check_command ros2
check_command gz
check_command colcon

if command -v ros2 >/dev/null 2>&1; then
  check_ros_package nav2_bringup
  check_ros_package nav2_msgs
  check_ros_package ros_gz_sim
fi

python3 --version || true
ros2 --help >/dev/null 2>&1 || true
gz sim --versions 2>/dev/null || gz sim --version 2>/dev/null || true

if (( failures > 0 )); then
  printf "\nEnvironment verification failed with %d problem(s).\n" "$failures" >&2
  exit 1
fi

printf "\nEnvironment verification passed.\n"
