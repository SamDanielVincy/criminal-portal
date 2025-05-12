from flask import Flask, render_template, Response, request, jsonify
import cv2
import os
from datetime import datetime
from email_alert import send_email_alert

from werkzeug.utils import secure_filename  # Add this import
from threading import Lock
import time
last_detected_id = None
last_detection_time = 0
detection_lock = Lock()

app = Flask(__name__)

# Initialize face recognizer and classifier
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("face_recognizer_OG.yml")
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Criminal database (ID: criminal data)
CRIMINAL_DB = {
    0: {
        "name": "Kumaravel",
        "crime": "Theift",
        "status": "Wanted",
        "details": "Wanted for 5 burglary cases in downtown area. Armed and dangerous.",
        "last_seen": "2023-10-15",
        "image": "static/images/kumaravel.jpg"
    },
    1: {
        "name": "Sivaneswaran",
        "crime": "Kidnapping",
        "status": "Wanted",
        "details": "Involved in identity theft and credit card fraud. Possibly armed.",
        "last_seen": "2023-11-02",
        "image": "static/images/Sivaneswaran.jpg"
    },
    2: {
        "name": "Sivaramakkanan",
        "crime": "Murder",
        "status": "Wanted",
        "details": "Wanted for 5 burglary cases in downtown area. Armed and dangerous.",
        "last_seen": "2023-10-15",
        "image": "static/images/sivaram.jpg"
    },
    3: {
        "name": "Subash",
        "crime": "Fraud",
        "status": "Wanted",
        "details": "Involved in identity theft and credit card fraud. Possibly armed.",
        "last_seen": "2023-11-02",
        "image": "static/images/Subash.jpg"
    }
}

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/')
def home():
    return render_template('index.html')

import threading  # Add this at the top of your file

def gen_frames():
    global last_detected_id, last_detection_time
    emailed_ids = set()
    camera = cv2.VideoCapture(0)

    while True:
        success, frame = camera.read()
        if not success:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            id, confidence = recognizer.predict(roi_gray)

            if confidence < 70:
                with detection_lock:
                    last_detected_id = id
                    last_detection_time = time.time()

                # Draw bounding box
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(frame, f"ID:{id}", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

                # Email alert in background
                if id not in emailed_ids:
                    criminal_info = CRIMINAL_DB.get(id, {})
                    threading.Thread(target=send_email_alert, args=(id, criminal_info)).start()
                    emailed_ids.add(id)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')



@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

from email_alert import send_email_alert  # Make sure this import is at the top

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # Save to temporary file
        temp_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        file.save(temp_path)

        # Open video with optimized settings
        cap = cv2.VideoCapture(temp_path)
        if not cap.isOpened():
            return jsonify({"error": "Could not open video"}), 400

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0

        target_frames = min(60, total_frames)
        skip_frames = max(1, int(total_frames / target_frames))

        detected_faces = set()
        emailed_ids = set()  # ✅ Track whom we've emailed already
        frame_count = 0
        processed_count = 0

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % skip_frames != 0:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=6,
                minSize=(50, 50),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            for (x, y, w, h) in faces:
                roi_gray = gray[y:y+h, x:x+w]
                id, confidence = recognizer.predict(roi_gray)
                if confidence < 70:
                    detected_faces.add(id)

                    # ✅ Only send email once per ID
                    if id not in emailed_ids:
                        criminal_info = CRIMINAL_DB.get(id, {})
                        send_email_alert(id, criminal_info)
                        emailed_ids.add(id)

                    break  # Only need one good detection per frame

            processed_count += 1
            if len(detected_faces) >= 3:
                break

        cap.release()
        os.remove(temp_path)

        return jsonify({
            "status": "success",
            "detected_faces": list(detected_faces),
            "processed_frames": processed_count,
            "total_frames": total_frames,
            "processing_time": f"{duration:.1f}s video → {processed_count} frames"
        })

    except Exception as e:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        return jsonify({"error": str(e)}), 500

@app.route('/criminal/<int:criminal_id>')
def get_criminal(criminal_id):
    return jsonify(CRIMINAL_DB.get(criminal_id, {}))

@app.route('/latest_detection')
def latest_detection():
    global last_detected_id, last_detection_time
    if last_detected_id is not None and (time.time() - last_detection_time) < 5:
        return jsonify({
            "id": last_detected_id,
            "criminal": CRIMINAL_DB.get(last_detected_id)
        })
    return jsonify({"id": None})


if __name__ == '__main__':
    app.run(debug=True)