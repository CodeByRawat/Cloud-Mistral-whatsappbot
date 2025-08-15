import os
import time
import base64
import requests
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("STABILITY_API_KEY")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate-video")
def generate_video(prompt: str = Form(...)):
    print(f"[DEBUG] Received prompt: {prompt}")

    # Step 1: Generate image from text
    image_url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    img_headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    img_data = {
        "prompt": prompt,
        "output_format": "png"
    }
    print("[DEBUG] Sending request to generate image...")
    img_resp = requests.post(image_url, headers=img_headers, json=img_data)
    print("[DEBUG] Image API response code:", img_resp.status_code)
    print("[DEBUG] Image API response body:", img_resp.text)

    if img_resp.status_code != 200:
        return {"error": img_resp.text}

    try:
        image_base64 = img_resp.json()["image"]
    except Exception as e:
        return {"error": f"Image parsing failed: {str(e)}"}

    image_bytes = base64.b64decode(image_base64)

    # Step 2: Send image to video API
    video_url = "https://api.stability.ai/v2beta/image-to-video"
    vid_headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    print("[DEBUG] Sending request to image-to-video API...")
    files = {"image": ("image.png", image_bytes, "image/png")}
    vid_resp = requests.post(video_url, headers=vid_headers, files=files)
    print("[DEBUG] Video API response code:", vid_resp.status_code)
    print("[DEBUG] Video API response body:", vid_resp.text)

    if vid_resp.status_code != 200:
        return {"error": vid_resp.text}

    job_id = vid_resp.json().get("id")
    if not job_id:
        return {"error": "No job ID returned from video API"}

    # Step 3: Poll until video is ready
    result_url = f"https://api.stability.ai/v2beta/image-to-video/result/{job_id}"
    print(f"[DEBUG] Polling for job ID: {job_id}")
    for attempt in range(20):  # ~100 seconds max
        res = requests.get(result_url, headers=vid_headers)
        print(f"[DEBUG] Poll {attempt+1} - code: {res.status_code} body: {res.text}")
        if res.status_code != 200:
            return {"error": res.text}
        result = res.json()
        if result.get("status") == "completed":
            return {"video_url": result.get("video_url")}
        time.sleep(5)

    return {"error": "Video generation timed out"}
