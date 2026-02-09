from flask import Flask, request, send_from_directory, jsonify
from ultralytics import YOLO
import os
import cv2
import gc
import yt_dlp
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from werkzeug.utils import secure_filename

# ================= PATHS =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
MODEL_PATH = os.path.join(BASE_DIR, "yolov8s.pt")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================= APP =================

app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path=""
)

app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

# ================= LOAD YOLO =================

print("Loading YOLO model...")

model = YOLO(MODEL_PATH)
model.to("cpu")

print("YOLO loaded successfully")

# ================= GLOBAL =================

video_summary = {}

# ================= GENDER (LAZY LOAD SAFE FOR RENDER) =================

def detect_gender(crop):

    try:

        if crop is None or crop.size == 0:
            return None

        from deepface import DeepFace

        result = DeepFace.analyze(
            crop,
            actions=['gender'],
            enforce_detection=False,
            silent=True
        )

        return result[0]["dominant_gender"]

    except Exception as e:

        print("Gender error:", e)
        return None

# ================= SUMMARY =================

def generate_scene_summary(male, female, object_freq):

    total = male + female

    sorted_objects = sorted(
        object_freq.items(),
        key=lambda x: x[1],
        reverse=True
    )

    objects = [obj for obj, count in sorted_objects[:5]]

    if "laptop" in objects or "cell phone" in objects:
        env = "a workspace or office environment"

    elif "dining table" in objects:
        env = "a dining or living area"

    elif "dog" in objects:
        env = "a home environment"

    else:
        env = "an indoor environment"

    return (
        f"The video shows {env}. "
        f"There are approximately {total} people "
        f"({male} males and {female} females). "
        f"Common objects include {', '.join(objects)}."
    )

# ================= FRONTEND ROUTES =================

@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/css/<path:path>")
def css(path):
    return send_from_directory(os.path.join(FRONTEND_DIR,"css"), path)

@app.route("/js/<path:path>")
def js(path):
    return send_from_directory(os.path.join(FRONTEND_DIR,"js"), path)

@app.route("/uploads/<path:path>")
def uploads(path):
    return send_from_directory(UPLOAD_DIR, path)

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)

# ================= FILE PROCESS =================

@app.route("/process", methods=["POST"])
def process():

    try:

        if "file" not in request.files:
            return jsonify({"error":"No file uploaded"})

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error":"Empty filename"})

        filename = secure_filename(file.filename)

        path = os.path.join(UPLOAD_DIR, filename)

        file.save(path)

        print("Saved:", path)

        if filename.lower().endswith((".jpg",".jpeg",".png",".webp")):
            return process_image(path)

        return process_video(path)

    except Exception as e:

        print("Process error:", e)
        return jsonify({"error":str(e)})

# ================= YOUTUBE PROCESS =================

@app.route("/process_link", methods=["POST"])
def process_link():

    try:

        data = request.json

        if not data or "url" not in data:
            return jsonify({"error":"No URL provided"})

        url = data["url"]

        output_path = os.path.join(UPLOAD_DIR, "youtube.mp4")

        if os.path.exists(output_path):
            os.remove(output_path)

        ydl_opts = {
            "format": "mp4",
            "outtmpl": output_path,
            "noplaylist": True,
            "quiet": True
        }

        print("Downloading YouTube video...")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        print("Download complete")

        return process_video(output_path)

    except Exception as e:

        print("YouTube error:", e)

        return jsonify({
            "error":"YouTube processing failed",
            "details":str(e)
        })

# ================= IMAGE PROCESS =================

def process_image(path):

    frame = cv2.imread(path)

    if frame is None:
        return jsonify({"error":"Invalid image"})

    results = model(frame, conf=0.25, device="cpu")

    male = 0
    female = 0
    object_freq = {}

    for box in results[0].boxes:

        cls = int(box.cls[0])
        name = model.names[cls]

        object_freq[name] = object_freq.get(name,0)+1

        if name == "person":

            x1,y1,x2,y2 = map(int, box.xyxy[0])

            crop = frame[y1:y2, x1:x2]

            gender = detect_gender(crop)

            if gender == "Man":
                male += 1

            elif gender == "Woman":
                female += 1

    summary = generate_scene_summary(male,female,object_freq)

    return jsonify({
        "male":male,
        "female":female,
        "unique_people":male+female,
        "visual_objects":list(object_freq.keys()),
        "content_summary":summary
    })

# ================= VIDEO PROCESS (RENDER SAFE) =================

def process_video(path):

    global video_summary

    cap = cv2.VideoCapture(path)

    male = 0
    female = 0
    object_freq = {}

    frame_count = 0

    print("Processing video ultra lightweight...")

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        frame_count += 1

        # Render safe optimization
        if frame_count % 60 != 0:
            continue

        gc.collect()

        results = model(frame, conf=0.25, device="cpu")

        for box in results[0].boxes:

            cls = int(box.cls[0])
            name = model.names[cls]

            object_freq[name] = object_freq.get(name,0)+1

            if name != "person":
                continue

            x1,y1,x2,y2 = map(int, box.xyxy[0])

            crop = frame[y1:y2, x1:x2]

            gender = detect_gender(crop)

            if gender == "Man":
                male += 1

            elif gender == "Woman":
                female += 1

    cap.release()

    summary = generate_scene_summary(male,female,object_freq)

    video_summary = {
        "male":male,
        "female":female,
        "unique_people":male+female,
        "visual_objects":list(object_freq.keys()),
        "content_summary":summary
    }

    print("Video done")

    return jsonify(video_summary)

# ================= CHAT =================

@app.route("/chat", methods=["POST"])
def chat():

    if not video_summary:
        return jsonify({"reply":"Analyze video first"})

    return jsonify({"reply":video_summary["content_summary"]})

# ================= PDF =================

@app.route("/export_pdf")
def export_pdf():

    path = os.path.join(UPLOAD_DIR,"report.pdf")

    c = canvas.Canvas(path,pagesize=A4)

    c.drawString(50,800,"VideoGPT Report")
    c.drawString(50,760,video_summary.get("content_summary",""))

    c.save()

    return send_from_directory(UPLOAD_DIR,"report.pdf",as_attachment=True)

# ================= RUN =================

if __name__ == "__main__":

    port = int(os.environ.get("PORT",10000))

    app.run(host="0.0.0.0",port=port)
