import os
import cv2
import numpy as np

from sklearn.neural_network import MLPClassifier

data_dir = "dataset_multiclass"

# Define any number of classes here
categories = ["Pen", "Bottle", "Cup", "Other"]

img_size = 64

features = []
labels = []

# --------------------
# 1. Dataset Collection Mode (Optional)
# --------------------
def collect_category(category_name):
    save_path = os.path.join(data_dir, category_name)
    os.makedirs(save_path, exist_ok=True)
    count = len(os.listdir(save_path))
    print(f"Collecting images for '{category_name}'. Press ENTER to capture, 'q' to stop.")
    while True:
        key = input(f"[{category_name}: {count}] Press ENTER or 'q': ").strip().lower()
        if key == 'q':
            break
        img_name = os.path.join(save_path, f"img_{count:03d}.jpg")
        os.system(f"rpicam-still -t 1 -o {img_name} --nopreview --width 640 --height 480")
        print(f"Saved -> {img_name}")
        count += 1

# --------------------
# 2. Load Dataset
# --------------------
print("--- Loading Multiclass Dataset ---")
for category in categories:
    path = os.path.join(data_dir, category)
    os.makedirs(path, exist_ok=True)
    class_num = categories.index(category)

    for img_name in os.listdir(path):
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

# --------------------
# 3. Train Model
# --------------------
if len(X) >= len(categories):
    model = MLPClassifier(
        hidden_layer_sizes=(64, 32),
        max_iter=500,
        random_state=42
    )
    model.fit(X, y)
    print(f"Multiclass Model Trained Successfully on {len(categories)} categories: {categories}")
else:
    print(f"Not enough dataset samples found in '{data_dir}/'. Please collect images for {categories} first.")
    model = None

temp_img = "current_view.jpg"

# --------------------
# 4. Live Prediction
# --------------------
if model is not None:
    print("Starting Live Multiclass Prediction. Press ENTER to classify, 'q' to quit.")
    while True:
        os.system(f"rpicam-still -t 10 -o {temp_img} --nopreview --width 640 --height 480")
        frame = cv2.imread(temp_img)
        if frame is None:
            break

        cv2.putText(
            frame,
            "Press ENTER to Classify | Q to Quit",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2
        )
        cv2.imshow("Multiclass Classifier", frame)
        key = cv2.waitKey(100)

        if key == ord('q'):
            break
        elif key == 13:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (img_size, img_size))
            flattened = resized.flatten().astype(np.float32) / 255.0

            prediction = model.predict([flattened])[0]
            label = categories[prediction]
            print(f"Prediction: {label} (Class {prediction})")

    cv2.destroyAllWindows()
