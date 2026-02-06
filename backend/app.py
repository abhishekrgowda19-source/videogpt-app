from flask import Flask, request, send_from_directory, jsonify
from ultralytics import YOLO
import os
import cv2
from PIL import Image
import yt_dlp
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# ================= PATHS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
MODEL_PATH = os.path.join(BASE_DIR, "models", "yolov8n.pt")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ================= APP =================
app = Flask(
    __name__,
    static_folder="../frontend",
    static_url_path=""
)
model = YOLO(MODEL_PATH)

# ================= GLOBAL STATE =================
video_summary = {}

# ================= FRONTEND =================
@app.route("/")
def home():
    return app.send_static_file("index.html")


@app.route("/css/<path:p>")
def css(p):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), p)

@app.route("/js/<path:p>")
def js(p):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), p)

# ================= PROCESS =================
@app.route("/process", methods=["POST"])
def process():
    file = request.files["file"]
    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)

    if path.lower().endswith((".jpg", ".png", ".jpeg", ".webp")):
        return process_image(path)
    else:
        return process_video(path)

# ================= IMAGE =================
def process_image(path):
    if path.endswith(".webp"):
        img = Image.open(path).convert("RGB")
        path = path.replace(".webp", ".jpg")
        img.save(path)

    results = model(path, imgsz=640, verbose=False)
    objects = {model.names[int(c)] for c in results[0].boxes.cls.tolist()}

    return jsonify({"visual_objects": list(objects)})

# ================= VIDEO =================
def process_video(path):
    global video_summary

    cap = cv2.VideoCapture(path)
    frame_count = 0
    object_freq = {}
    person_ids = set()

    FRAME_SKIP = 12  # speed + stability

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % FRAME_SKIP != 0:
            continue

        results = model.track(
            frame,
            persist=True,
            conf=0.4,
            imgsz=480,
            verbose=False
        )

        if not results or not results[0].boxes:
            continue

        for box in results[0].boxes:
            cls_name = model.names[int(box.cls[0])]
            object_freq[cls_name] = object_freq.get(cls_name, 0) + 1

            if cls_name == "person" and box.id is not None:
                person_ids.add(int(box.id[0]))

    cap.release()

    summary = (
        f"The video contains {len(object_freq)} object types. "
        f"{len(person_ids)} unique people appear in the video. "
        f"Most common objects: "
        f"{', '.join(sorted(object_freq, key=object_freq.get, reverse=True)[:5])}."
    )

    video_summary = {
        "unique_people": len(person_ids),
        "visual_objects": list(object_freq.keys()),
        "content_summary": summary,
        "download_video": f"/uploads/{os.path.basename(path)}"
    }

    return jsonify(video_summary)

# ================= YOUTUBE =================
@app.route("/process_link", methods=["POST"])
def process_link():
    url = request.json["url"]
    path = os.path.join(UPLOAD_DIR, "youtube.mp4")

    with yt_dlp.YoutubeDL({
        "outtmpl": path,
        "format": "mp4",
        "quiet": True
    }) as ydl:
        ydl.download([url])

    return process_video(path)

# ================= CHAT =================
@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json["message"].lower().strip()

    if not video_summary:
        return jsonify({
            "reply": "Please analyze a video first, then ask me questions 🙂"
        })

    people = video_summary["unique_people"]
    objects = video_summary["visual_objects"]
    summary = video_summary["content_summary"]

    if "people" in msg or "persons" in msg:
        return jsonify({"reply": f"There are {people} unique people in the video."})

    if "object" in msg or "inside" in msg:
        return jsonify({
            "reply": f"I detected objects such as: {', '.join(objects[:8])}"
            if objects else "No clear objects were detected."
        })

    if "summary" in msg or "explain" in msg:
        return jsonify({"reply": summary})

    return jsonify({
        "reply": (
            "You can ask me:\n"
            "• How many people are in the video\n"
            "• What objects are present\n"
            "• Give me a summary of the video"
        )
    })

# ================= PDF EXPORT =================
@app.route("/export_pdf", methods=["GET"])
def export_pdf():
    if not video_summary:
        return jsonify({"error": "Analyze a video first"}), 400

    pdf_path = os.path.join(UPLOAD_DIR, "VideoGPT_Report.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 22)
    c.drawString(50, y, "VideoGPT – Video Analysis Report")
    y -= 40

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Generated on: {datetime.now().strftime('%d %b %Y, %H:%M')}")
    y -= 30

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Summary")
    y -= 20

    c.setFont("Helvetica", 11)
    text = c.beginText(50, y)
    for line in video_summary["content_summary"].split(". "):
        text.textLine(line.strip())
    c.drawText(text)

    c.showPage()
    c.save()

    return send_from_directory(UPLOAD_DIR, "VideoGPT_Report.pdf", as_attachment=True)

# ================= RUN =================
p# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    print(f"🚀 VideoGPT running on port {port}")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
