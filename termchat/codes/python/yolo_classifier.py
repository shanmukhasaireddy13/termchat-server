import os
import sys
import shutil
import subprocess

# ---------------------------------------------------------
# 1. Package Dependency Check
# ---------------------------------------------------------
missing_pkgs = []
try:
    import cv2
except ImportError:
    missing_pkgs.append(("opencv-python", "pip install opencv-python"))

try:
    from ultralytics import YOLO
except ImportError:
    missing_pkgs.append(("ultralytics", "pip install ultralytics"))

if missing_pkgs:
    print("Missing required package(s):")
    for pkg_name, cmd in missing_pkgs:
        print(f"  {pkg_name} -> Run: {cmd}")
    print("\nOn Raspberry Pi OS:")
    print("  sudo apt update && sudo apt install -y python3-opencv python3-pip")
    print("  pip install ultralytics --break-system-packages")
    sys.exit(1)

# ---------------------------------------------------------
# 2. Camera Capture via rpicam-still
# ---------------------------------------------------------
TEMP_IMAGE = "current_capture.jpg"


def capture_frame(output_path=TEMP_IMAGE):
    """
    Captures a frame using Raspberry Pi rpicam-still (with libcamera-still
    and OpenCV VideoCapture fallbacks for maximum hardware compatibility).
    """
    # 1. rpicam-still (standard for Raspberry Pi Camera Module on Pi OS Bookworm)
    if shutil.which("rpicam-still"):
        cmd = [
            "rpicam-still",
            "-t", "10",
            "-o", output_path,
            "--nopreview",
            "--width", "640",
            "--height", "480",
        ]
        ret = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ret.returncode == 0 and os.path.exists(output_path):
            img = cv2.imread(output_path)
            if img is not None:
                return img

    # 2. libcamera-still (Raspberry Pi Bullseye fallback)
    if shutil.which("libcamera-still"):
        cmd = [
            "libcamera-still",
            "-t", "10",
            "-o", output_path,
            "--nopreview",
            "--width", "640",
            "--height", "480",
        ]
        ret = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ret.returncode == 0 and os.path.exists(output_path):
            img = cv2.imread(output_path)
            if img is not None:
                return img

    # 3. OpenCV VideoCapture fallback (V4L2 or USB webcam)
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        success, img = cap.read()
        cap.release()
        if success and img is not None:
            return img

    return None


# ---------------------------------------------------------
# 3. Model Initialization (Auto-downloads on first run)
# ---------------------------------------------------------
print("Loading pretrained YOLO model...")
model = YOLO("yolov8n.pt")
print("Model ready. Camera initialized.")

# ---------------------------------------------------------
# 4. Main Inference Loop
# ---------------------------------------------------------
try:
    while True:
        try:
            choice = input("\n[Enter] Take photo | [q] Quit: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if choice == "q":
            break

        frame = capture_frame(TEMP_IMAGE)
        if frame is None:
            print("Error: Could not capture image from camera.")
            print("Check camera connection or run: rpicam-still -t 1000 -o test.jpg")
            continue

        results = model(frame, verbose=False)
        boxes = results[0].boxes

        if len(boxes) == 0:
            print("No objects detected.")
        else:
            print("Detected objects:")
            for box in boxes:
                cls_id = int(box.cls[0])
                label = model.names[cls_id]
                conf = float(box.conf[0]) * 100
                print(f"  - {label}: {conf:.1f}%")

finally:
    if os.path.exists(TEMP_IMAGE):
        try:
            os.remove(TEMP_IMAGE)
        except OSError:
            pass
    print("Camera released. Exiting.")
