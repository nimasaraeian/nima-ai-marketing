from fastapi import FastAPI, UploadFile, File

from fastapi.responses import JSONResponse

import numpy as np

from PIL import Image

import io

import os

import tensorflow as tf

import traceback



app = FastAPI(title="Visual Trust Service", version="1.0")



MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

keras_files = [f for f in os.listdir(MODELS_DIR) if f.endswith(".keras")]

if not keras_files:

    raise RuntimeError(f"No .keras model found in {MODELS_DIR}")



MODEL_PATH = os.path.join(MODELS_DIR, keras_files[0])

model = None



CLASS_NAMES = ["low", "medium", "high"]



def load_model_once():

    global model

    if model is None:

        model = tf.keras.models.load_model(MODEL_PATH)



def preprocess_image(file_bytes: bytes) -> np.ndarray:

    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")

    img = img.resize((224, 224))

    arr = np.array(img).astype("float32") / 255.0

    return np.expand_dims(arr, axis=0)



@app.get("/health")

def health():

    try:

        load_model_once()

        return {

            "ok": True,

            "modelLoaded": True,

            "modelFile": os.path.basename(MODEL_PATH)

        }

    except Exception as e:

        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})



@app.post("/analyze")

async def analyze(file: UploadFile = File(...)):

    try:

        load_model_once()



        try:

            raw = await file.read()

            if not raw or len(raw) < 1000:

                return JSONResponse(status_code=400, content={"analysisStatus":"error","error":"Empty or too small file"})



            img = Image.open(io.BytesIO(raw))

            img = img.convert("RGB")  # fixes RGBA/alpha and weird modes



            # hard safety limit: if huge screenshot, shrink first

            max_side = 1600

            w, h = img.size

            if max(w, h) > max_side:

                scale = max_side / float(max(w, h))

                img = img.resize((int(w*scale), int(h*scale)), Image.BILINEAR)



            # model input size (use 224x224 as default; keep if your code already defines a target)

            target = (224, 224)

            img = img.resize(target, Image.BILINEAR)



            x = np.asarray(img, dtype=np.float32) / 255.0

            x = np.expand_dims(x, axis=0)  # [1,224,224,3]



            # then run model.predict(x) exactly as before, no other logic changes



        except Exception as e:

            return JSONResponse(

                status_code=503,

                content={

                    "analysisStatus":"error",

                    "errorType": type(e).__name__,

                    "error": str(e),

                    "traceback": traceback.format_exc()[:2000],

                    "hint": "Image decode/preprocess failed. Ensure RGB conversion + resize."

                }

            )



        preds = model.predict(x, verbose=0)[0]

        idx = int(np.argmax(preds))



        return {

            "analysisStatus": "ok",

            "label": CLASS_NAMES[idx],

            "confidence": float(preds[idx]),

            "probs": {

                CLASS_NAMES[i]: float(preds[i])

                for i in range(len(CLASS_NAMES))

            }

        }



    except Exception as e:

        return JSONResponse(

            status_code=503,

            content={

                "analysisStatus":"error",

                "errorType": type(e).__name__,

                "error": str(e),

                "traceback": traceback.format_exc()[:2000]

            }

        )

