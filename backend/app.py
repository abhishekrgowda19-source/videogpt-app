from flask import Flask, request, jsonify
from ultralytics import YOLO
import os
import cv2
import gc
from werkzeug.utils import secure_filename

# ================= CONFIG =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

MODEL_PATH = os.path.join(BASE_DIR, "yolov8s.pt")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

# IMPORTANT FOR RENDER (limit size)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024


# ================= LOAD MODEL =================

print("Loading YOLO model...")

try:

    model = YOLO(MODEL_PATH)

    model.to("cpu")

    print("YOLO loaded successfully")

except Exception as e:

    print("MODEL LOAD ERROR:", e)

    model = None


video_summary = {}


# ================= TEST ROUTES =================

@app.route("/")
def home():
    return "VideoGPT Backend Running"


@app.route("/test")
def test():
    return "Backend OK"


# ================= PROCESS =================

@app.route("/process", methods=["POST"])
def process():

    try:

        if model is None:
            return jsonify({"error": "Model not loaded"}), 500

        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        filename = secure_filename(file.filename)

        path = os.path.join(UPLOAD_DIR, filename)

        file.save(path)

        print("Saved:", path)

        return process_video(path)

    except Exception as e:

        print("PROCESS ERROR:", e)

        return jsonify({"error": str(e)}), 500


# ================= VIDEO PROCESS =================

def process_video(path):

    cap = cv2.VideoCapture(path)

    if not cap.isOpened():
        return jsonify({"error": "Cannot open video"}), 400

    return analyze_video(cap)


# ================= SAFE ANALYSIS =================

def analyze_video(cap):

    global video_summary

    person_count = 0
    object_freq = {}

    frame_count = 0
    MAX_FRAMES = 10   # VERY IMPORTANT → prevents crash

    print("Starting safe analysis...")

    while cap.isOpened():

        ret, frame = cap.read()

        if not ret:
            break

        frame_count += 1

        # STOP early to prevent memory crash
        if frame_count > MAX_FRAMES:
            break

        # analyze every 3rd frame
        if frame_count % 3 != 0:
            continue

        try:

            results = model.predict(
                frame,
                conf=0.4,
                imgsz=320,   # smaller size → less RAM
                device="cpu",
                verbose=False
            )

            if results and results[0].boxes is not None:

                for box in results[0].boxes:

                    name = model.names[int(box.cls[0])]

                    object_freq[name] = object_freq.get(name, 0) + 1

                    if name == "person":
                        person_count += 1

        except Exception as e:
            print("Detection error:", e)

        gc.collect()

    cap.release()

    summary = f"Detected {person_count} persons. Objects: {list(object_freq.keys())}"

    video_summary = {
        "person_count": person_count,
        "visual_objects": list(object_freq.keys()),
        "content_summary": summary
    }

    print("Completed safely")

    return jsonify(video_summary)

# ================= RUN =================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
