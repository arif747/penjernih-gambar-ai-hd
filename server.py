import os
import io
import asyncio
from typing import Optional
import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, JSONResponse, FileResponse
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Penjernih Gambar AI HD")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def home():
    return FileResponse(Path(__file__).parent / "index.html")

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "").strip()
MODEL_OWNER = os.getenv("REPLICATE_MODEL_OWNER", "nightmareai")
MODEL_NAME = os.getenv("REPLICATE_MODEL_NAME", "real-esrgan")
MAX_BYTES = 10 * 1024 * 1024

@app.get("/api/health")
async def health():
    return {"ok": True, "token_configured": bool(REPLICATE_API_TOKEN)}

@app.post("/api/enhance")
async def enhance(
    image: UploadFile = File(...),
    scale: int = Form(2),
    face_enhance: bool = Form(True),
    format: str = Form("png"),
):
    if not REPLICATE_API_TOKEN:
        raise HTTPException(status_code=503, detail="API token belum dipasang. Ikuti langkah REPLICATE_API_TOKEN di README.md.")
    if scale not in (2, 4):
        raise HTTPException(status_code=400, detail="Skala harus 2 atau 4.")
    if format not in ("png", "jpg"):
        raise HTTPException(status_code=400, detail="Format harus PNG atau JPG.")
    content_type = (image.content_type or "").lower()
    if content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail="Gunakan gambar JPG, PNG, atau WebP.")
    data = await image.read(MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="File gambar kosong.")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Ukuran gambar maksimum 10 MB.")
    # Replicate's hosted model accepts an image URL or data URI. Sending a data URI
    # keeps the sample self-contained; large uploads may be rejected by provider limits.
    import base64
    encoded = base64.b64encode(data).decode("ascii")
    data_uri = f"data:{content_type};base64,{encoded}"
    payload = {
        "input": {
            "image": data_uri,
            "scale": scale,
            "face_enhance": face_enhance,
        }
    }
    headers = {"Authorization": f"Bearer {REPLICATE_API_TOKEN}", "Content-Type": "application/json", "Prefer": "wait"}
    api_url = f"https://api.replicate.com/v1/models/{MODEL_OWNER}/{MODEL_NAME}/predictions"
    timeout = httpx.Timeout(180.0, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            r = await client.post(api_url, headers=headers, json=payload)
            if r.status_code >= 400:
                detail = "Penyedia AI menolak permintaan."
                try:
                    body = r.json()
                    detail = body.get("detail") or body.get("title") or body.get("error") or detail
                except Exception:
                    pass
                raise HTTPException(status_code=502, detail=f"Replicate: {detail}")
            pred = r.json()
            # Prefer-wait often returns completed prediction; otherwise poll its URL.
            deadline = asyncio.get_running_loop().time() + 150
            while pred.get("status") in ("starting", "processing") and pred.get("urls", {}).get("get"):
                if asyncio.get_running_loop().time() > deadline:
                    raise HTTPException(status_code=504, detail="Model AI terlalu lama merespons. Coba lagi.")
                await asyncio.sleep(2)
                poll = await client.get(pred["urls"]["get"], headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"})
                poll.raise_for_status()
                pred = poll.json()
            if pred.get("status") != "succeeded":
                err = pred.get("error") or pred.get("status") or "status tidak diketahui"
                raise HTTPException(status_code=502, detail=f"Proses AI gagal: {err}")
            output = pred.get("output")
            if isinstance(output, list):
                output_url = output[0] if output else None
            else:
                output_url = output
            if not isinstance(output_url, str) or not output_url.startswith("https://"):
                raise HTTPException(status_code=502, detail="Model tidak mengembalikan URL gambar yang valid.")
            out = await client.get(output_url)
            out.raise_for_status()
            raw = out.content
            media = "image/png"
            if format == "jpg":
                try:
                    from PIL import Image
                    im = Image.open(io.BytesIO(raw)).convert("RGB")
                    buf = io.BytesIO()
                    im.save(buf, format="JPEG", quality=94, optimize=True)
                    raw = buf.getvalue()
                    media = "image/jpeg"
                except ImportError:
                    raise HTTPException(status_code=500, detail="Pillow belum terpasang. Jalankan pip install -r requirements.txt.")
            return Response(content=raw, media_type=media, headers={"Cache-Control": "no-store"})
        except HTTPException:
            raise
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Waktu koneksi ke layanan AI habis. Coba lagi.")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Koneksi layanan AI gagal: {str(exc)[:200]}")
