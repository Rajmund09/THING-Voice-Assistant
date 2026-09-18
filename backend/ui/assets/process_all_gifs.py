import os
from PIL import Image, ImageSequence
from rembg import remove, new_session
import io

input_dir = r"c:\Users\prabh\OneDrive\Documents\GitHub\THING-Voice-Assistant\backend\ui\assets"
files_to_process = {
    "working and thiking.gif": "thinking.gif",
    "walkingg.gif": "walking.gif",
    "speaking.gif": "speaking.gif",
    "listening.gif": "listening.gif"
}

session = new_session()

for in_name, out_name in files_to_process.items():
    in_path = os.path.join(input_dir, in_name)
    out_path = os.path.join(input_dir, out_name)
    if not os.path.exists(in_path):
        print(f"Skipping {in_name}, not found.")
        continue

    print(f"Processing {in_name}...")
    try:
        img = Image.open(in_path)
        frames = []
        for frame in ImageSequence.Iterator(img):
            # Process each frame
            frame_rgba = frame.convert("RGBA")
            # We can use rembg directly on PIL Image in modern rembg versions
            # But let's be safe and use bytes if PIL fails, or just use PIL
            res_frame = remove(frame_rgba, session=session)
            frames.append(res_frame)

        if frames:
            frames[0].save(
                out_path,
                save_all=True,
                append_images=frames[1:],
                duration=img.info.get('duration', 50),
                loop=img.info.get('loop', 0),
                disposal=2 # Important for transparent GIFs
            )
        print(f"Successfully processed {in_name} -> {out_name}")
    except Exception as e:
        print(f"Failed to process {in_name}: {e}")

# Flip walking.gif to walking_left.gif
walking_path = os.path.join(input_dir, "walking.gif")
walking_left_path = os.path.join(input_dir, "walking_left.gif")
if os.path.exists(walking_path):
    print("Flipping walking.gif to walking_left.gif...")
    try:
        img = Image.open(walking_path)
        frames = []
        for frame in ImageSequence.Iterator(img):
            frames.append(frame.transpose(Image.FLIP_LEFT_RIGHT))
        
        frames[0].save(
            walking_left_path,
            save_all=True,
            append_images=frames[1:],
            duration=img.info.get('duration', 50),
            loop=img.info.get('loop', 0),
            disposal=2
        )
        print("Flipped successfully.")
    except Exception as e:
        print(f"Failed to flip walking.gif: {e}")
