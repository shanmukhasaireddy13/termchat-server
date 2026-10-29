"""
termchat.codes.runner
---------------------
Execution and deployment runner for termchat robotics, BeetleBot,
and ROS 2 embedded scripts.

Allows zero-friction execution directly from CLI:
  termchat run obstacle
  termchat run color
  termchat run slam
  termchat run turtlesim
  termchat setup-lyra
  termchat export-codes
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

from termchat.codes import (
    CODES_DIR,
    PYTHON_DIR,
    ARDUINO_DIR,
    COMMANDS_GUIDE,
    BEETLEBOT_GUIDE,
    TURTLESIM_GUIDE,
    OPERATION_MANUAL,
)

SCRIPT_MAP = {
    # BeetleBot Autonomous Robotics
    "obstacle": "obstacle_avoidance.py",
    "obstacle_avoid": "obstacle_avoidance.py",
    "obstacle_avoidance": "obstacle_avoidance.py",
    "color": "color_navigation.py",
    "color_nav": "color_navigation.py",
    "color_navigation": "color_navigation.py",
    "arrow": "arrow_navigation.py",
    "arrow_nav": "arrow_navigation.py",
    "arrow_navigation": "arrow_navigation.py",
    "slam": "beetle_slam_mapper.py",
    "mapper": "beetle_slam_mapper.py",
    "beetle_slam": "beetle_slam_mapper.py",
    "beetle_slam_mapper": "beetle_slam_mapper.py",

    # BeetleBot Automated Motion Sequences & Safety
    "arm": "beetlebot_motion_sequences.py",
    "disarm": "beetlebot_motion_sequences.py",
    "forward": "beetlebot_motion_sequences.py",
    "backward": "beetlebot_motion_sequences.py",
    "stop": "beetlebot_motion_sequences.py",
    "halt": "beetlebot_motion_sequences.py",
    "square": "beetlebot_motion_sequences.py",
    "seq": "beetlebot_motion_sequences.py",
    "patrol": "beetlebot_motion_sequences.py",
    "teleop": "beetlebot_motion_sequences.py",
    "beetle_motion": "beetlebot_motion_sequences.py",
    "motion": "beetlebot_motion_sequences.py",

    # Turtlesim Multi-Turtle & Shapes
    "turtlesim": "turtlesim_three_turtles.py",
    "three_turtles": "turtlesim_three_turtles.py",
    "turtles": "turtlesim_three_turtles.py",
    "shapes": "turtlesim_shapes.py",
    "turtle_shapes": "turtlesim_shapes.py",

    # Raspberry Pi & Vision
    "traffic": "traffic.py",
    "distance": "distance.py",
    "dataset": "binary_classifier_dataset.py",
    "train_live": "binary_classifier_train_live.py",
    "classifier": "multiclass_classifier.py",
    "multiclass": "multiclass_classifier.py",
    "yolo": "yolo_classifier.py",
    "yolo_classifier": "yolo_classifier.py",
    "yolo_cls": "yolo_classifier.py",
    "pretrained": "yolo_classifier.py",
    "pretrained_classifier": "yolo_classifier.py",
}


def list_available():
    """Prints all runnable scripts and sketches."""
    print("=" * 65)
    print("          TERMCHAT EMBEDDED & ROBOTICS SCRIPTS")
    print("=" * 65)
    print("\n[BeetleBot ROS 2 Jazzy Autonomous Experiments]")
    print("  termchat run obstacle     -> LiDAR Autonomous Obstacle Avoidance")
    print("  termchat run color        -> Vision Color Card Navigation (Green/Yellow/Red)")
    print("  termchat run arrow        -> Vision Arrow Direction Navigation (Left/Right)")
    print("  termchat run slam         -> 2D LiDAR SLAM, Frontier Exploration & ArUco")
    print("  termchat setup-lyra       -> 1-Click setup ~/lyra_ws (NO nano, NO pasting!)")

    print("\n[BeetleBot Motion Sequences & Safety (/cmd_vel_nav)]")
    print("  termchat run arm          -> Electronic Arming Call (/lyra/arm)")
    print("  termchat run disarm       -> Emergency Disarm Call (/lyra/disarm)")
    print("  termchat run forward      -> Move Forward 5s + forced stop")
    print("  termchat run backward     -> Move Backward 5s + forced stop")
    print("  termchat run stop         -> Emergency Flood Stop (20 Hz halt)")
    print("  termchat run square       -> Square Path Sequence (4 sides)")
    print("  termchat run seq          -> Advanced Patrol (Forward -> Stop -> Backward -> Stop)")
    print("  termchat run teleop       -> Keyboard Teleop remapped to /cmd_vel_nav")

    print("\n[ROS 2 Turtlesim Multi-Robot & Shape Suite]")
    print("  termchat run turtlesim    -> 3 Turtle Simultaneous Coordinated Movement")
    print("  termchat run shapes       -> Custom Shape Drawing (Star, Circle, Square, Spiral)")

    print("\n[Raspberry Pi IoT & Vision AI]")
    print("  termchat run traffic      -> 4-Way Dynamic Adaptive Traffic Controller")
    print("  termchat run distance     -> Ultrasonic HC-SR04 Sonar with Alarm")
    print("  termchat run classifier   -> Multi-Class Machine Learning Suite")
    print("  termchat run yolo         -> Pretrained YOLO Multi-Class Classifier (rpicam-still)")

    print("\n[Arduino Sketches (In 'termchat export-codes')]")
    for f in sorted(ARDUINO_DIR.glob("*.ino")):
        print(f"  • {f.name}")

    print("\n[Guides & Manuals]")
    print(f"  • {COMMANDS_GUIDE.name}")
    print(f"  • {BEETLEBOT_GUIDE.name}")
    print(f"  • {TURTLESIM_GUIDE.name}")
    print(f"  • {OPERATION_MANUAL.name}")
    print("=" * 65)


def run_script(name, extra_args=None):
    """Executes a target script by alias or filename."""
    if extra_args is None:
        extra_args = []

    clean_name = name.lower().strip()
    target_file = SCRIPT_MAP.get(clean_name)
    if not target_file:
        # Check if direct filename match in python directory
        candidate = PYTHON_DIR / name
        if candidate.is_file():
            target_file = candidate.name
        else:
            print(f"[Error] Unknown script '{name}'.")
            print("Run 'termchat run list' to see all available scripts.")
            return 1

    # If invoking motion sequence alias, automatically pass alias command
    if target_file == "beetlebot_motion_sequences.py" and not extra_args:
        extra_args = [clean_name]

    script_path = PYTHON_DIR / target_file
    if not script_path.is_file():
        print(f"[Error] Script file not found: {script_path}")
        return 1

    print(f"\n[TermChat] Launching: {target_file}")
    print(f"[TermChat] Path: {script_path}\n" + "-" * 55)

    # For Linux / ROS 2 nodes: check if we need to wrap with bash sourcing
    is_ros2 = target_file in (
        "obstacle_avoidance.py",
        "color_navigation.py",
        "arrow_navigation.py",
        "beetle_slam_mapper.py",
        "beetlebot_motion_sequences.py",
        "turtlesim_three_turtles.py",
        "turtlesim_shapes.py",
    )

    if sys.platform.startswith("linux") and is_ros2:
        # Check if rclpy is directly importable in current python environment
        try:
            import rclpy
            # Environment is already sourced! Run directly with current interpreter
            cmd = [sys.executable, str(script_path)] + extra_args
            return subprocess.call(cmd)
        except ImportError:
            # Not yet sourced in current subshell; wrap with bash -c
            setup_jazzy = "/opt/ros/jazzy/setup.bash"
            setup_humble = "/opt/ros/humble/setup.bash"
            setup_ws = os.path.expanduser("~/lyra_ws/install/setup.bash")

            sources = []
            if os.path.isfile(setup_jazzy):
                sources.append(f"source {setup_jazzy}")
            elif os.path.isfile(setup_humble):
                sources.append(f"source {setup_humble}")

            if os.path.isfile(setup_ws):
                sources.append(f"source {setup_ws}")

            args_str = " ".join(f'"{a}"' for a in extra_args)
            if sources:
                bash_cmd = f"{' && '.join(sources)} && python3 \"{script_path}\" {args_str}"
                return subprocess.call(["bash", "-c", bash_cmd])

    # Default direct execution
    cmd = [sys.executable, str(script_path)] + extra_args
    return subprocess.call(cmd)


def setup_lyra_workspace():
    """
    Automates BeetleBot Lyra package setup without nano, Ctrl+K, or manual copy-pasting!
    1. Copies obstacle_avoidance.py, color_navigation.py, arrow_navigation.py,
       and beetle_slam_mapper.py to ~/lyra_ws/src/lyra_control/lyra_control/
    2. Sets executable permissions.
    3. Injects console_scripts entry_point into ~/lyra_ws/src/lyra_control/setup.py if needed.
    4. Automatically runs colcon build.
    """
    print("\n" + "=" * 65)
    print("      BEETLEBOT AUTOMATED 1-CLICK LYRA WORKSPACE SETUP")
    print("=" * 65)

    home = Path.home()
    lyra_src = home / "lyra_ws" / "src" / "lyra_control" / "lyra_control"
    setup_py = home / "lyra_ws" / "src" / "lyra_control" / "setup.py"
    lyra_ws = home / "lyra_ws"

    if not lyra_ws.is_dir():
        print(f"[Warning] ~/lyra_ws directory not detected at {lyra_ws}.")
        print("[Info] Creating target directories...")

    lyra_src.mkdir(parents=True, exist_ok=True)

    scripts_to_deploy = [
        "obstacle_avoidance.py",
        "color_navigation.py",
        "arrow_navigation.py",
        "beetle_slam_mapper.py",
        "beetlebot_motion_sequences.py",
    ]

    print(f"\n[1/4] Deploying Python nodes to {lyra_src}...")
    for s in scripts_to_deploy:
        src = PYTHON_DIR / s
        dst = lyra_src / s
        if src.is_file():
            shutil.copy2(src, dst)
            if sys.platform != "win32":
                dst.chmod(0o755)
            print(f"  ✓ Installed: {s}")

    # Step 2: Check & update setup.py entry_points
    print("\n[2/4] Verifying ROS 2 setup.py entry points...")
    if setup_py.is_file():
        content = setup_py.read_text(encoding="utf-8")
        needed_entry = "'obstacle_avoid = lyra_control.obstacle_avoidance:main'"
        if "obstacle_avoid = lyra_control.obstacle_avoidance:main" not in content:
            if "'console_scripts': [" in content:
                content = content.replace(
                    "'console_scripts': [",
                    f"'console_scripts': [\n            {needed_entry},"
                )
                setup_py.write_text(content, encoding="utf-8")
                print("  ✓ Registered 'obstacle_avoid' in setup.py console_scripts!")
            else:
                print("  [Notice] console_scripts block not found in setup.py; script can still be run via python3.")
        else:
            print("  ✓ Entry point 'obstacle_avoid' already present in setup.py.")
    else:
        print(f"  [Info] No setup.py at {setup_py}. Standalone python3 execution is ready!")

    # Step 3: Run colcon build
    print("\n[3/4] Building package with colcon...")
    if lyra_ws.is_dir() and shutil.which("colcon"):
        res = subprocess.call(
            ["colcon", "build", "--packages-select", "lyra_control"],
            cwd=str(lyra_ws)
        )
        if res == 0:
            print("  ✓ colcon build completed successfully!")
        else:
            print("  [Warning] colcon build returned non-zero code. You can still run with 'python3 obstacle_avoidance.py'.")
    else:
        print("  [Info] colcon build skipped (colcon not found or not in workspace).")

    print("\n[4/4] COMPLETE!")
    print("-" * 65)
    print("You can now run obstacle avoidance using EITHER command:")
    print("  A) ros2 run lyra_control obstacle_avoid")
    print("  B) python3 ~/lyra_ws/src/lyra_control/lyra_control/obstacle_avoidance.py")
    print("  C) termchat run obstacle")
    print("=" * 65 + "\n")
    return 0


def export_codes(destination=None):
    """Exports all code files and guides to destination folder."""
    if not destination:
        destination = Path.cwd() / "codes"
    else:
        destination = Path(destination)

    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CODES_DIR, destination, dirs_exist_ok=True)
    print(f"\n[OK] Successfully exported all codes to: {destination.resolve()}")
    print("Exported files include Arduino sketches, Python modules, and guides.\n")
    return 0
