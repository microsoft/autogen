import sqlite3
import sys
import json
import os
import base64
import subprocess
import textwrap
from PIL import Image, ImageDraw, ImageFont

OUTPUT = "/mnt/c/Users/adamfo/Desktop/frames"

def main():

    task = sys.argv[1]
    delete_all_files_in_directory(OUTPUT)

    prompt = ""
    with open(os.path.join(task, "task_prompt.json"), "rt") as fh:
        prompt = json.loads(fh.read())["intent"]

    make_slide(prompt, os.path.join(OUTPUT, "0000.png"))
    make_slide(prompt, os.path.join(OUTPUT, "0001.png"))

    con = sqlite3.connect(os.path.join(task, "telemetry.sqlite"))
    cur = con.cursor()

    idx = 2 
    
    client_id = cur.execute("SELECT wrapper_id FROM agents WHERE name='web_surfer'").fetchone()[0]
    for row in cur.execute("SELECT request FROM chat_completions WHERE wrapper_id = ? ORDER BY start_time ASC;", (client_id,)):
        data = json.loads(row[0])

        last_message = data["messages"][-1]
        
        if isinstance(last_message["content"], list):
            for entry in last_message["content"]:
                if entry["type"] == "image_url":
                    image = entry["image_url"]["url"]
                    if image.startswith("data:image/png;base64,"):
                        image = base64.b64decode(image[len("data:image/png;base64,"):])

                        fname = str(idx)
                        idx = idx + 1
                        while len(fname) < 4:
                            fname = "0" + fname
                        fname = os.path.join(OUTPUT, fname + ".png")
                        print("saving " + fname)
                        with open(fname, "wb") as fh:
                            fh.write(image)


    log = ""
    with open(os.path.join(task, "console_log.txt"), "rt") as fh:
        log = fh.read()

    fname = str(idx)
    idx = idx + 1
    while len(fname) < 4:
        fname = "0" + fname
    fname = os.path.join(OUTPUT, fname + ".png")

    if "FINAL SCORE: 1.0" in log:
        make_slide("SUCCESS", os.path.join(OUTPUT, fname))
    elif "FINAL SCORE: 0.0" in log:
        make_slide("FAIL", os.path.join(OUTPUT, fname))
    else:
        make_slide("INCOMPLETE", os.path.join(OUTPUT, fname))

    result = subprocess.run("ffmpeg -framerate 1 -i " + os.path.join(OUTPUT, "%04d.png") + " -s:v 1224x764 -c:v libx264 -crf 17 -pix_fmt yuv420p -filter:v \"setpts=2*PTS\" -y " + os.path.join(task, "video.mp4"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Print the output (both stdout and stderr)
    #print("Standard Output:")
    #print(result.stdout)

    #print("\nStandard Error:")
    #print(result.stderr)


def make_slide(text, fname):
    width, height = 1124, 765
    image = Image.new("RGB", (width, height), "black")

    # Initialize the drawing context
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(30)

    # Define the text and position
    text_position = (562, 382)

    lines = textwrap.wrap(text, width=40)

    # Draw the text on the image
    draw.multiline_text(text_position, "\n".join(lines), fill="white", font=font, anchor="mm", align="center")
    image.save(fname)

def delete_all_files_in_directory(directory_path):
    files = os.listdir(directory_path)
    for file in files:
        file_path = os.path.join(directory_path, file)
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"Deleted file: {file_path}")

main()
