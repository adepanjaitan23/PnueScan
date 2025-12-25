import os
import random
from datetime import datetime

import numpy as np
from flask import Flask, render_template, request, redirect, url_for
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

# konfigurasi dasar
IMG_SIZE = (224, 224)
THRESHOLD = 0.5

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
REF_FOLDER = os.path.join(BASE_DIR, "static", "references")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# load model
MODEL_PATH = os.path.join(BASE_DIR, "model.h5")
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model tidak ditemukan: {MODEL_PATH}")

model = load_model(MODEL_PATH)

ALLOWED_EXT = {"jpg", "jpeg", "png"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def predict_xray(filepath: str, target_size=IMG_SIZE, thr=THRESHOLD):
    img = image.load_img(filepath, target_size=target_size)
    x = image.img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)

    prob_pneu = float(model.predict(x, verbose=0)[0, 0])

    if prob_pneu >= thr:
        label = "PNEUMONIA"
        confidence = prob_pneu
    else:
        label = "NORMAL"
        confidence = 1.0 - prob_pneu

    return {
        "label": label,
        "prob_pneumonia": prob_pneu,
        "confidence": confidence
    }

def get_reference_images(label: str, max_images: int = 6):
    """
    Ambil sampai max_images path relatif gambar referensi dari static/references/<label>/
    """
    label_dir = os.path.join(REF_FOLDER, label)
    if not os.path.isdir(label_dir):
        return []

    files = [
        f for f in os.listdir(label_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if not files:
        return []

    k = min(max_images, len(files))
    chosen = random.sample(files, k)

    return [f"/static/references/{label}/{fname}" for fname in chosen]

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/predict", methods=["GET", "POST"])
def predict():
    if request.method == "GET":
        return render_template("predict.html")

    if "image" not in request.files:
        return render_template("predict.html", error_msg="Field image tidak ditemukan.")

    file = request.files["image"]
    if file.filename == "":
        return render_template("predict.html", error_msg="Tidak ada file yang dipilih.")

    if not allowed_file(file.filename):
        return render_template("predict.html", error_msg="Format file harus JPG, JPEG, atau PNG.")

    # simpan file upload dengan nama unik
    ext = file.filename.rsplit(".", 1)[1].lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"xray_{timestamp}.{ext}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    try:
        result = predict_xray(save_path)
        ref_images = get_reference_images(result["label"])

        # path relatif untuk ditampilkan di HTML
        uploaded_rel_path = f"/static/uploads/{filename}"

        return render_template(
            "predict.html",
            uploaded_image=uploaded_rel_path,
            prediction=result,
            ref_images=ref_images,
            threshold=THRESHOLD
        )
    except Exception as e:
        return render_template("predict.html", error_msg=f"Terjadi error saat prediksi: {str(e)}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)