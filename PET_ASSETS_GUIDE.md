# Desktop Pet Asset Guide

If you ever want to add your `clicking.gif`, `idle.gif`, `scrolling.gif`, or `typing.gif` back into the project, just follow these exact steps to ensure they are processed perfectly like the current animations!

## 1. Place the files
Put your raw GIFs inside the `backend/ui/assets` folder. For example:
- `backend/ui/assets/idle.gif`
- `backend/ui/assets/scrolling.gif`

## 2. Run the Background Remover
To perfectly remove the background from all the frames without destroying the animation, use the script I wrote for you earlier:

1. Open a terminal in the root of the project.
2. Run the processing script:
   ```bash
   python backend/ui/assets/process_all_gifs.py
   ```
*(Note: You will need to edit `process_all_gifs.py` to include `"idle.gif": "idle.gif"` in the `files_to_process` dictionary at the top of the file before running it)*

## 3. Update the Pet Logic
Right now, the pet is programmed to roam around and "think" when it is idle because it doesn't have an `idle.gif`! 
If you want it to stand perfectly still again, you need to open `backend/ui/desktop_pet.py` and modify `trigger_random_walk()` to not fire constantly, or let the `load_movie` function successfully find your new `idle.gif`.

Currently, it falls back to `walking` or `thinking` automatically if a GIF is missing, ensuring it always looks like a highly intelligent AI.
