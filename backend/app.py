from flask import Flask, request, send_from_directory, jsonify
from ultralytics import YOLO
import os
import cv2
import gc
import yt_dlp
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from werkzeug.utils import secure_filename

# ================= PATH SETUP =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
MODEL_PATH = os.path.join(BASE_DIR, "yolov8s.pt")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ================= APP INIT =================

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

# ================= LOAD MODEL =================

print("Loading YOLO model...")

model = YOLO(MODEL_PATH)
model.to("cpu")

print("YOLO loaded successfully")

# ================= GLOBAL =================

video_summary = {}

# ================= TEST ROUTE =================

@app.route("/")
def home():
    return "VideoGPT Backend is running"

@app.route("/test")
def test():
    return "Backend is working"

# ================= SUMMARY =================

def generate_scene_summary(person_count, object_freq):

    sorted_objects = sorted(
        object_freq.items(),
        key=lambda x: x[1],
        reverse=True
    )

    objects = [obj for obj, count in sorted_objects[:5]]

    if "laptop" in objects:
        env = "a workspace or office environment"
    elif "dining table" in objects:
        env = "a dining area"
    elif "car" in objects:
        env = "an outdoor street environment"
    elif "dog" in objects:
        env = "a home environment"
    else:
        env = "an indoor environment"

    objects_text = ", ".join(objects) if objects else "no major objects detected"

    return (
        f"The video shows {env}. "
        f"There are approximately {person_count} people present. "
        f"Common objects include {objects_text}."
    )

# ================= PROCESS FILE =================

@app.route("/process", methods=["POST"])
def process():

    try:

        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_DIR, filename)

        file.save(path)

        print("File saved:", path)

        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            return process_image(path)

        return process_video(path)

    except Exception as e:

        print("Process error:", e)
        return jsonify({"error": str(e)}), 500

# ================= IMAGE =================

def process_image(path):

    frame = cv2.imread(path)

    if frame is None:
        return jsonify({"error": "Invalid image"}), 400

    person_count = 0
    object_freq = {}

    results = model.predict(
        frame,
        conf=0.25,
        imgsz=320,
        device="cpu",
        verbose=False
    )

    if results and results[0].boxes is not None:

        for box in results[0].boxes:

            cls = int(box.cls[0])
            name = model.names[cls]

            object_freq[name] = object_freq.get(name, 0) + 1

            if name == "person":
                person_count += 1

    summary = generate_scene_summary(person_count, object_freq)

    result = {
        "person_count": person_count,
        "visual_objects": list(object_freq.keys()),
        "content_summary": summary
    }

    print("Image result:", result)

    return jsonify(result)

# ================= VIDEO =================

def process_video(path):

    cap = cv2.VideoCapture(path)

    if not cap.isOpened():
        return jsonify({"error": "Cannot open video"}), 400

    return analyze_video(cap)

# ================= VIDEO STREAM =================

@app.route("/process_link", methods=["POST"])
def process_link():

    try:

        data = request.get_json()

        if not data or "url" not in data:
            return jsonify({"error": "No URL provided"}), 400

        url = data["url"]

        ydl_opts = {
            "quiet": True,
            "format": "worst",
            "noplaylist": True,
            "skip_download": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=False)
            stream_url = info["url"]

        cap = cv2.VideoCapture(stream_url)

        if not cap.isOpened():
            return jsonify({"error": "Cannot open stream"}), 400

        return analyze_video(cap)

    except Exception as e:

        print("YouTube error:", e)
        return jsonify({"error": str(e)}), 500

# ================= CORE ANALYSIS =================

def analyze_video(cap):

    global video_summary

    person_count = 0
    object_freq = {}

    frame_count = 0
    MAX_FRAMES = 30  # prevent timeout

    print("Starting video analysis...")

    while cap.isOpened():

        ret, frame = cap.read()

        if not ret:
            break

        frame_count += 1

        if frame_count > MAX_FRAMES:
            print("Stopping early to avoid timeout")
            break

        if frame_count % 10 != 0:
            continue

        try:

            gc.collect()

            results = model.predict(
                frame,
                conf=0.3,
                imgsz=320,
                device="cpu",
                verbose=False
            )

            if results and results[0].boxes is not None:

                for box in results[0].boxes:

                    cls = int(box.cls[0])
                    name = model.names[cls]

                    object_freq[name] = object_freq.get(name, 0) + 1

                    if name == "person":
                        person_count += 1

            print(f"Frame {frame_count} | Persons: {person_count}")

        except Exception as e:
            print("Frame error:", e)

    cap.release()

    summary = generate_scene_summary(person_count, object_freq)

    video_summary = {
        "person_count": person_count,
        "visual_objects": list(object_freq.keys()),
        "content_summary": summary
    }

    print("Final summary:", video_summary)

    return jsonify(video_summary)

# ================= CHAT =================

@app.route("/chat", methods=["POST"])
def chat():

    if not video_summary:
        return jsonify({"reply": "Analyze video first"})

    return jsonify({"reply": video_summary["content_summary"]})

# ================= PDF =================

@app.route("/export_pdf")
def export_pdf():

    path = os.path.join(UPLOAD_DIR, "report.pdf")

    c = canvas.Canvas(path, pagesize=A4)

    c.drawString(50, 800, "VideoGPT Report")
    c.drawString(50, 760, video_summary.get("content_summary", ""))

    c.save()

    return send_from_directory(
        UPLOAD_DIR,
        "report.pdf",
        as_attachment=True
    )

# ================= RUN =================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    print("Server running on port:", port)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
