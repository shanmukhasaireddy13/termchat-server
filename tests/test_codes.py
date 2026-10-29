import pytest
from pathlib import Path
import termchat.codes as tc


def test_codes_structure():
    assert tc.CODES_DIR.is_dir()
    assert tc.ARDUINO_DIR.is_dir()
    assert tc.PYTHON_DIR.is_dir()
    assert tc.COMMANDS_GUIDE.is_file()
    assert tc.BEETLEBOT_GUIDE.is_file()
    assert tc.TURTLESIM_GUIDE.is_file()


def test_arduino_sketches_exist():
    expected_sketches = [
        "car_park.ino",
        "square_motion.ino",
        "circle_motion.ino",
        "line_following.ino",
        "maze_solving.ino",
    ]
    for sketch in expected_sketches:
        p = tc.ARDUINO_DIR / sketch
        assert p.is_file(), f"Missing {sketch}"
        assert p.stat().st_size > 0


def test_python_scripts_exist():
    expected_scripts = [
        "traffic.py",
        "distance.py",
        "binary_classifier_dataset.py",
        "binary_classifier_train_live.py",
        "multiclass_classifier.py",
        "obstacle_avoidance.py",
        "color_navigation.py",
        "arrow_navigation.py",
        "beetle_slam_mapper.py",
        "beetlebot_motion_sequences.py",
        "turtlesim_three_turtles.py",
        "turtlesim_shapes.py",
    ]
    for script in expected_scripts:
        p = tc.PYTHON_DIR / script
        assert p.is_file(), f"Missing {script}"
        assert p.stat().st_size > 0


def test_guide_files_content():
    guide = tc.COMMANDS_GUIDE.read_text(encoding="utf-8")
    assert "car_park.ino" in guide
    assert "traffic.py" in guide
    assert "multiclass_classifier.py" in guide
    assert "TURTLESIM" in guide
    assert "VEEROBOT BEETLE BOT (LYRA) OPERATION" in guide

    beetle = tc.BEETLEBOT_GUIDE.read_text(encoding="utf-8")
    assert "EXPERIMENT 1: 2D LiDAR AUTONOMOUS OBSTACLE AVOIDANCE" in beetle
    assert "EXPERIMENT 2: VISION-BASED AUTONOMOUS NAVIGATION" in beetle
    assert "EXPERIMENT 3: 2D LiDAR SLAM, FRONTIER EXPLORATION & LANDMARK MAPPING" in beetle
    assert "SQUARE PATH SEQUENCE" in beetle
    assert "KEYBOARD TELEOP" in beetle

    turtle = tc.TURTLESIM_GUIDE.read_text(encoding="utf-8")
    assert "THREE TURTLE SIMULTANEOUS MOVEMENT" in turtle
    assert "FIVE-POINTED STAR" in turtle
    assert "PERFECT CIRCLE" in turtle

    op = tc.OPERATION_MANUAL.read_text(encoding="utf-8")
    assert "192.168.0.128" in op
    assert "/lyra/arm" in op
    assert "/lyra/disarm" in op
    assert "/cmd_vel_nav" in op
    assert "teleop_twist_keyboard" in op


def test_runner_aliases():
    from termchat.codes.runner import SCRIPT_MAP
    assert SCRIPT_MAP["forward"] == "beetlebot_motion_sequences.py"
    assert SCRIPT_MAP["backward"] == "beetlebot_motion_sequences.py"
    assert SCRIPT_MAP["square"] == "beetlebot_motion_sequences.py"
    assert SCRIPT_MAP["stop"] == "beetlebot_motion_sequences.py"
    assert SCRIPT_MAP["teleop"] == "beetlebot_motion_sequences.py"
