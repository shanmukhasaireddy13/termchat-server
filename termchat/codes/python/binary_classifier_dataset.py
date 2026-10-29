import os
import subprocess

category = "Other"        # Change to "Pen" while collecting pen images

save_dir = os.path.join("dataset", category)
os.makedirs(save_dir, exist_ok=True)

img_count = len(os.listdir(save_dir))

print("=" * 50)
print(f"Saving photos to: {save_dir}")
print("Press ENTER to capture image")
print("Press q + ENTER to quit")
print("=" * 50)

while True:

    user_input = input(
        f"[Captured: {img_count}] Press ENTER to capture (or q): "
    )

    if user_input.strip().lower() == "q":
        break

    img_name = os.path.join(
        save_dir,
        f"img_{img_count:03d}.jpg"
    )

    cmd = [
        "rpicam-still",
        "-t",
        "1",
        "-o",
        img_name,
        "--nopreview"
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"Saved -> {img_name}")
        img_count += 1

    except Exception as e:
        print(e)
        break

print("Dataset Collection Finished")
