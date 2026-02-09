from flask import Flask, request, send_from_directory, jsonify
from ultralytics import YOLO
import os
import cv2
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from werkzeug.utils import secure_filename
from deepface import DeepFace


# ================= PATHS =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# FIXED: frontend inside backend
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

MODEL_PATH = os.path.join(BASE_DIR, "yolov8s.pt")

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ================= APP =================

app = Flask(__name__)


# ================= LOAD YOLO =================

print("Loading YOLO model...")
model = YOLO(MODEL_PATH)
print("YOLO loaded successfully")


# ================= GLOBAL STATE =================

video_summary = {}


# ================= GENDER DETECTION =================

def detect_gender(crop):

    try:
        result = DeepFace.analyze(
            crop,
            actions=['gender'],
            enforce_detection=False,
            silent=True
        )
        return result[0]["dominant_gender"]

    except:
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
        environment = "a workspace or office environment"

    elif "dining table" in objects:
        environment = "a dining or living area"

    elif "dog" in objects:
        environment = "a home environment"

    else:
        environment = "an indoor environment"

    summary = (
        f"The video shows {environment}. "
        f"There are approximately {total} unique people present "
        f"({male} males and {female} females). "
        f"Common objects include {', '.join(objects)}."
    )

    return summary


# ================= FRONTEND ROUTES =================

@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/css/<path:path>")
def serve_css(path):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), path)


@app.route("/js/<path:path>")
def serve_js(path):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), path)


@app.route("/uploads/<path:path>")
def serve_uploads(path):
    return send_from_directory(UPLOAD_DIR, path)


# IMPORTANT fallback route
@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)


# ================= PROCESS =================

@app.route("/process", methods=["POST"])
def process():

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"})

    file = request.files["file"]

    filename = secure_filename(file.filename)

    path = os.path.join(UPLOAD_DIR, filename)

    file.save(path)

    if filename.lower().endswith((".jpg",".jpeg",".png",".webp")):
        return process_image(path)

    return process_video(path)


# ================= IMAGE =================

def process_image(path):

    frame = cv2.imread(path)

    results = model(frame, conf=0.25)

    male_ids = set()
    female_ids = set()

    object_freq = {}

    if results[0].boxes is not None:

        for box in results[0].boxes:

            cls_id = int(box.cls[0])
            name = model.names[cls_id]

            object_freq[name] = object_freq.get(name,0)+1

            if name == "person":

                x1,y1,x2,y2 = map(int, box.xyxy[0])

                crop = frame[y1:y2, x1:x2]

                gender = detect_gender(crop)

                if gender == "Man":
                    male_ids.add(id(box))

                elif gender == "Woman":
                    female_ids.add(id(box))


    male = len(male_ids)
    female = len(female_ids)

    summary = generate_scene_summary(male,female,object_freq)

    return jsonify({
        "male": male,
        "female": female,
        "unique_people": male+female,
        "visual_objects": list(object_freq.keys()),
        "content_summary": summary
    })


# ================= VIDEO WITH TRACKING =================

def process_video(path):

    global video_summary

    male_ids = set()
    female_ids = set()
    all_ids = set()

    object_freq = {}

    results = model.track(
        source=path,
        conf=0.25,
        persist=True,
        stream=True,
        tracker="bytetrack.yaml"
    )

    for r in results:

        if r.boxes is None:
            continue

        frame = r.orig_img

        boxes = r.boxes.xyxy.cpu().numpy()
        classes = r.boxes.cls.cpu().numpy()
        ids = r.boxes.id

        if ids is None:
            continue

        ids = ids.cpu().numpy()

        for box, cls_id, track_id in zip(boxes, classes, ids):

            name = model.names[int(cls_id)]

            object_freq[name] = object_freq.get(name,0)+1

            if name != "person":
                continue

            if track_id in all_ids:
                continue

            x1,y1,x2,y2 = map(int, box)

            crop = frame[y1:y2, x1:x2]

            gender = detect_gender(crop)

            if gender == "Man":
                male_ids.add(track_id)
                all_ids.add(track_id)

            elif gender == "Woman":
                female_ids.add(track_id)
                all_ids.add(track_id)


    male = len(male_ids)
    female = len(female_ids)

    summary = generate_scene_summary(male,female,object_freq)

    video_summary = {
        "male": male,
        "female": female,
        "unique_people": male+female,
        "visual_objects": list(object_freq.keys()),
        "content_summary": summary
    }

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

    pdf_path = os.path.join(UPLOAD_DIR,"report.pdf")

    c = canvas.Canvas(pdf_path,pagesize=A4)

    c.drawString(50,800,"VideoGPT Report")
    c.drawString(50,760,video_summary.get("content_summary",""))

    c.save()

    return send_from_directory(UPLOAD_DIR,"report.pdf",as_attachment=True)


# ================= RUN =================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
