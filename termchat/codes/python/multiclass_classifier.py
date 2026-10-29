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

data_dir = "dataset_multiclass"
categories = ["Pen", "Bottle", "Cup", "Other"]
img_size = 64
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


# 2. Collect Mode (if requested via command line)
if len(sys.argv) > 1 and sys.argv[1] == "collect":
    cat_to_collect = sys.argv[2] if len(sys.argv) > 2 else "Other"
    save_path = os.path.join(data_dir, cat_to_collect)
    os.makedirs(save_path, exist_ok=True)
    count = len([f for f in os.listdir(save_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    print(f"Collecting images for '{cat_to_collect}'. Press ENTER to capture, 'q' to stop.")
    while True:
        try:
            key = input(f"[{cat_to_collect}: {count}] Press ENTER or 'q': ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break
        if key == 'q':
            break
        img_name = os.path.join(save_path, f"img_{count:03d}.jpg")
        frame = capture_frame(img_name)
        if frame is not None:
            print(f"Saved -> {img_name}")
            count += 1
        else:
            print("Failed to capture image.")
    print("Collection ended.")
    sys.exit(0)

# 3. Load Dataset
features = []
labels = []
print("--- Loading Multiclass Dataset ---")
for category in categories:
    path = os.path.join(data_dir, category)
    os.makedirs(path, exist_ok=True)
    class_num = categories.index(category)

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

# 4. Train Model
unique_labels = np.unique(y) if len(y) > 0 else []
if len(X) >= len(categories) and len(unique_labels) >= 2:
    model = MLPClassifier(
        hidden_layer_sizes=(64, 32),
        max_iter=500,
        random_state=42
    )
    model.fit(X, y)
    print(f"Multiclass Model Trained Successfully on categories: {categories}")
else:
    print(f"Notice: Not enough dataset samples found in '{data_dir}/'.")
    print(f"Found {len(X)} samples across classes {list(unique_labels)}.")
    print(f"Please collect images for categories {categories} first by running:")
    print("  python multiclass_classifier.py collect <CategoryName>")
    model = None

# 5. Live Prediction
if model is not None:
    print("\nStarting Live Multiclass Prediction.")
    print("Press ENTER to classify, 'q' to quit.")
    try:
        while True:
            try:
                user_key = input("\n[Enter] Classify | [q] Quit: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                break

            if user_key == 'q':
                break

            frame = capture_frame(temp_img)
            if frame is None:
                print("Failed to capture image from camera.")
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (img_size, img_size))
            flattened = resized.flatten().astype(np.float32) / 255.0

            prediction = model.predict([flattened])[0]
            label = categories[prediction]
            print(f"Prediction: {label} (Class {prediction})")

            if os.environ.get("DISPLAY"):
                try:
                    cv2.putText(frame, f"Class: {label}", (20, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    cv2.imshow("Multiclass Classifier", frame)
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
