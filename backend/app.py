from flask import Flask, request, jsonify
from ultralytics import YOLO
import os
import cv2
import gc
from werkzeug.utils import secure_filename

# ================= CONFIG =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
MODEL_PATH = os.path.join(BASE_DIR, "yolov8n.pt")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

# IMPORTANT: 30MB limit (Render safe)
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024


# ================= LOAD MODEL =================

print("Loading YOLOv8n model...")

model = YOLO(MODEL_PATH)

# IMPORTANT OPTIMIZATION
model.fuse()

print("Model loaded successfully")


# ================= HEALTH =================

@app.route("/")
def home():
    return "Backend running OK"

@app.route("/test")
def test():
    return "Backend OK"


# ================= PROCESS =================

@app.route("/process", methods=["POST"])
def process():

    try:

        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]

        filename = secure_filename(file.filename)

        path = os.path.join(UPLOAD_DIR, filename)

        file.save(path)

        print("Saved:", path)

        return analyze_video(path)

    except Exception as e:

        print("Error:", e)

        return jsonify({"error": str(e)}), 500


# ================= SAFE ANALYSIS =================

def analyze_video(path):

    try:

        cap = cv2.VideoCapture(path)

        if not cap.isOpened():
            return jsonify({"error": "Cannot open video"}), 400

        person_count = 0
        object_freq = {}

        # CRITICAL: ONLY 1 FRAME
        cap.set(cv2.CAP_PROP_POS_FRAMES, 5)

        ret, frame = cap.read()

        cap.release()

        if not ret:
            return jsonify({"error": "Cannot read frame"}), 400

        # CRITICAL: reduce resolution
        frame = cv2.resize(frame, (320, 320))

        # SINGLE inference only
        results = model.predict(
            frame,
            conf=0.4,
            imgsz=320,
            device="cpu",
            verbose=False
        )

        if results and results[0].boxes is not None:

            for box in results[0].boxes:

                name = model.names[int(box.cls[0])]

                object_freq[name] = object_freq.get(name, 0) + 1

                if name == "person":
                    person_count += 1


        gc.collect()

        summary = {
            "person_count": person_count,
            "visual_objects": list(object_freq.keys()),
            "content_summary":
                f"Detected {person_count} persons. Objects: {list(object_freq.keys())}"
        }

        print("SUCCESS:", summary)

        return jsonify(summary)

    except Exception as e:

        print("Analysis error:", e)

        return jsonify({"error": str(e)}), 500


# ================= RUN =================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)
