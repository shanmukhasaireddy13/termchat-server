import os
import cv2
import numpy as np

from sklearn.neural_network import MLPClassifier

data_dir = "dataset"

categories = ["Other", "Pen"]

img_size = 64

features = []
labels = []

# --------------------
# Load Dataset
# --------------------

for category in categories:

    path = os.path.join(data_dir, category)

    class_num = categories.index(category)

    if not os.path.exists(path):
        continue

    for img_name in os.listdir(path):

        img_path = os.path.join(path, img_name)

        img = cv2.imread(
            img_path,
            cv2.IMREAD_GRAYSCALE
        )

        if img is None:
            continue

        resized = cv2.resize(
            img,
            (img_size, img_size)
        )

        flattened = resized.flatten().astype(np.float32) / 255.0

        features.append(flattened)

        labels.append(class_num)

X = np.array(features)

y = np.array(labels)

# --------------------
# Train Model
# --------------------

model = MLPClassifier(
    hidden_layer_sizes=(32,),
    max_iter=500,
    random_state=42
)

model.fit(X, y)

print("Model Trained Successfully")

temp_img = "current_view.jpg"

# --------------------
# Live Prediction
# --------------------

while True:

    os.system(
        f"rpicam-still -t 10 -o {temp_img} --nopreview --width 640 --height 480"
    )

    frame = cv2.imread(temp_img)

    if frame is None:
        break

    cv2.putText(
        frame,
        "Press ENTER to Classify | Q to Quit",
        (20,30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0,255,255),
        2
    )

    cv2.imshow("Pen Classifier", frame)

    key = cv2.waitKey(100)

    if key == ord('q'):
        break

    elif key == 13:

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        resized = cv2.resize(
            gray,
            (img_size,img_size)
        )

        flattened = resized.flatten().astype(np.float32)/255.0

        prediction = model.predict([flattened])[0]

        label = "PEN" if prediction == 1 else "NOT PEN"

        print("Prediction :", label)

cv2.destroyAllWindows()
