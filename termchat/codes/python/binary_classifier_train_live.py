import os
import sys
import shutil
import subprocess

# 1. Dependency Check
missing_pkgs = []
try:
    import cv2
except ImportError:
    missing_pkgs.append(("opencv-python", "pip install opencv-python"))

try:
    import numpy as np
except ImportError:
    missing_pkgs.append(("numpy", "pip install numpy"))

try:
    from sklearn.neural_network import MLPClassifier
except ImportError:
    missing_pkgs.append(("scikit-learn", "pip install scikit-learn"))

if missing_pkgs:
    print("Missing required package(s):")
    for pkg_name, cmd in missing_pkgs:
        print(f"  {pkg_name} -> Run: {cmd}")
    print("\nOn Raspberry Pi OS:")
    print("  sudo apt update && sudo apt install -y python3-opencv python3-numpy python3-sklearn")
    sys.exit(1)

data_dir = "dataset"
categories = ["Other", "Pen"]
img_size = 64

features = []
labels = []

# 2. Load Dataset
print("Loading binary dataset...")
for category in categories:
    path = os.path.join(data_dir, category)
    class_num = categories.index(category)

    if not os.path.exists(path):
        continue

    for img_name in os.listdir(path):
        if not img_name.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        img_path = os.path.join(path, img_name)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        resized = cv2.resize(img, (img_size, img_size))
        flattened = resized.flatten().astype(np.float32) / 255.0
        features.append(flattened)
        labels.append(class_num)

X = np.array(features)
y = np.array(labels)

# Check sample sufficiency
unique_classes = np.unique(y) if len(y) > 0 else []
if len(X) < 2 or len(unique_classes) < 2:
    print(f"Error: Insufficient dataset samples in '{data_dir}/'.")
    print(f"Found {len(X)} samples across classes {list(unique_classes)}.")
    print("Both 'dataset/Other' and 'dataset/Pen' require at least 1 image to train.")
    print("\nTo collect images first, run:")
    print("  python binary_classifier_dataset.py Other")
    print("  python binary_classifier_dataset.py Pen")
    sys.exit(1)

# 3. Train Model
print(f"Training binary MLP classifier on {len(X)} samples...")
model = MLPClassifier(
    hidden_layer_sizes=(32,),
    max_iter=500,
    random_state=42
)
model.fit(X, y)
print("Model Trained Successfully.")

temp_img = "current_view.jpg"


def capture_frame(output_path=temp_img):
    if shutil.which("rpicam-still"):
        cmd = ["rpicam-still", "-t", "10", "-o", output_path, "--nopreview", "--width", "640", "--height", "480"]
        ret = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ret.returncode == 0 and os.path.exists(output_path):
            return cv2.imread(output_path)

    if shutil.which("libcamera-still"):
        cmd = ["libcamera-still", "-t", "10", "-o", output_path, "--nopreview", "--width", "640", "--height", "480"]
        ret = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ret.returncode == 0 and os.path.exists(output_path):
            return cv2.imread(output_path)

    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None:
            return frame

    return None


# 4. Live Prediction Loop
print("\nStarting live prediction.")
print("[Enter] Classify current view | [q] Quit")

try:
    while True:
        try:
            user_key = input("\nPress ENTER to classify (or 'q' to quit): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if user_key == 'q':
            break

        frame = capture_frame(temp_img)
        if frame is None:
            print("Error: Could not capture frame from camera.")
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (img_size, img_size))
        flattened = resized.flatten().astype(np.float32) / 255.0

        prediction = model.predict([flattened])[0]
        label = "PEN" if prediction == 1 else "NOT PEN"
        print(f"Prediction: {label} (Class {prediction})")

        # Optional GUI display if X11 / display server is present
        if os.environ.get("DISPLAY"):
            try:
                cv2.putText(frame, f"Prediction: {label}", (20, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.imshow("Pen Classifier", frame)
                if cv2.waitKey(500) & 0xFF == ord('q'):
                    break
            except cv2.error:
                pass

finally:
    if os.path.exists(temp_img):
        try:
            os.remove(temp_img)
        except OSError:
            pass
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass
    print("Classifier finished.")
