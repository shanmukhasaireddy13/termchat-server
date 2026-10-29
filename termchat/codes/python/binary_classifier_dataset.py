import os
import sys
import shutil
import subprocess

# Determine category
category = sys.argv[1] if len(sys.argv) > 1 else "Other"
print(f"Target Category: {category} (Change by running: python binary_classifier_dataset.py <CategoryName>)")

save_dir = os.path.join("dataset", category)
os.makedirs(save_dir, exist_ok=True)

img_count = len([f for f in os.listdir(save_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])

print("=" * 50)
print(f"Saving photos to: {save_dir}")
print("Press ENTER to capture image")
print("Press q + ENTER to quit")
print("=" * 50)


def capture_single(target_path):
    if shutil.which("rpicam-still"):
        cmd = ["rpicam-still", "-t", "1", "-o", target_path, "--nopreview", "--width", "640", "--height", "480"]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0 and os.path.exists(target_path)

    if shutil.which("libcamera-still"):
        cmd = ["libcamera-still", "-t", "1", "-o", target_path, "--nopreview", "--width", "640", "--height", "480"]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0 and os.path.exists(target_path)

    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                cv2.imwrite(target_path, frame)
                return True
    except ImportError:
        pass

    return False


while True:
    try:
        user_input = input(f"[{category}: {img_count} images] Press ENTER to capture (or q to exit): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        break

    if user_input == "q":
        break

    img_name = os.path.join(save_dir, f"img_{img_count:03d}.jpg")

    success = capture_single(img_name)
    if success:
        print(f"Saved -> {img_name}")
        img_count += 1
    else:
        print("Camera capture failed. Ensure Raspberry Pi camera or webcam is connected.")
        print("Required command: rpicam-still (or python package: opencv-python)")
        break

print("Dataset Collection Finished.")
