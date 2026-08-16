from __future__ import annotations

import json
import math
from io import BytesIO
from numbers import Real
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from PIL import Image, ImageChops
import cv2
import numpy as np

app = FastAPI(title="Core image extensions")


def _schema(title: str, properties: dict, required: list[str], *, require_image=True, **meta):
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "additionalProperties": False, "title": title, "properties": properties, "required": required, "x-hint-require-image": require_image, **meta}


def _num(name, title, default, minimum, maximum, step, typ="number"):
    result = {"type": typ, "title": title, "default": default, "minimum": minimum, "x-hint-ui-step": step, "x-hint-ui-control": "slider" if typ == "number" else "number"}
    if maximum is not None:
        result["maximum"] = maximum
    return result


def validate_crop(o):
    vals = tuple(o.get(k) for k in ("x", "y", "width", "height"))
    if any(isinstance(v, bool) or not isinstance(v, Real) or not math.isfinite(v) for v in vals): raise ValueError("Invalid crop rectangle")
    x, y, w, h = vals
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 1 or y + h > 1: raise ValueError("Invalid crop rectangle")
    return dict(zip(("x", "y", "width", "height"), vals))


def validate_rotate(o):
    d = o.get("degrees")
    if isinstance(d, bool) or not isinstance(d, int) or d % 90: raise ValueError("Invalid rotate degrees")
    return {"degrees": d % 360}


def validate_straighten(o):
    a = o.get("angle")
    if isinstance(a, bool) or not isinstance(a, Real) or not math.isfinite(a) or abs(a) > 45: raise ValueError("Invalid straighten angle")
    a = round(a * 10) / 10
    return {"angle": 0.0 if a == 0 else a}


def validate_trim(o):
    result = {}
    for edge in ("top", "right", "bottom", "left"):
        v = o.get(edge)
        if isinstance(v, bool) or not isinstance(v, int) or v < 0: raise ValueError("Invalid trim edge")
        result[edge] = v
    return result


MODELS = ["birefnet-general", "birefnet-portrait", "isnet-general", "isnet-anime", "u2net", "silueta"]
def validate_remove(o):
    model = o.get("model", "birefnet-general")
    if model not in MODELS: raise ValueError("Invalid background removal model")
    result = {"model": model}
    for key in ("alpha_matting", "post_process_mask"):
        if not isinstance(o.get(key, False), bool): raise ValueError("Invalid background removal flag")
        result[key] = o.get(key, False)
    for key, default in (("alpha_matting_foreground_threshold", 128), ("alpha_matting_background_threshold", 128)):
        value = o.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255: raise ValueError("Invalid background removal threshold")
        result[key] = value
    value = o.get("alpha_matting_erode_size", 10)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 100: raise ValueError("Invalid background removal erode size")
    result["alpha_matting_erode_size"] = value
    return result


SCHEMAS = {
 "crop": _schema("Crop", {k: _num(k, k.title(), d, 0, 1, .001) for k, d in (("x",0),("y",0),("width",1),("height",1))}, ["x","y","width","height"], x_hint_icon="Crop169"),
 "rotate": _schema("Rotate", {"degrees": _num("degrees", "Degrees", 0, 0, 270, 90, "integer")}, ["degrees"], x_hint_icon="Rotate90DegreesCcw"),
 "straighten": _schema("Straighten", {"angle": _num("angle", "Angle", 0, -45, 45, .1)}, ["angle"], x_hint_icon="Straighten"),
 "trim": _schema("Trim", {k: _num(k, k.title(), 0, 0, None, 1, "integer") for k in ("top","right","bottom","left")}, ["top","right","bottom","left"], x_hint_icon="ContentCut"),
 "remove_background": _schema("Remove Background", {"model": {"type":"string","enum":MODELS,"default":"birefnet-general"}, "alpha_matting":{"type":"boolean","default":False}, "alpha_matting_foreground_threshold":{"type":"integer","minimum":0,"maximum":255,"default":128}, "alpha_matting_background_threshold":{"type":"integer","minimum":0,"maximum":255,"default":128}, "alpha_matting_erode_size":{"type":"integer","minimum":1,"maximum":100,"default":10}, "post_process_mask":{"type":"boolean","default":False}}, ["model","alpha_matting","alpha_matting_foreground_threshold","alpha_matting_background_threshold","alpha_matting_erode_size","post_process_mask"], x_hint_icon="AutoFixHigh"),
}
# _schema's keyword spelling is intentionally normalized here for valid JSON metadata.
for schema in SCHEMAS.values():
    if "x_hint_icon" in schema: schema["x-hint-icon"] = schema.pop("x_hint_icon")

VALIDATORS = {"crop": validate_crop, "rotate": validate_rotate, "straighten": validate_straighten, "trim": validate_trim, "remove_background": validate_remove}


def _image(data: bytes):
    try:
        with Image.open(BytesIO(data)) as image:
            return image.convert("RGBA")
    except Exception as exc: raise ValueError("Invalid PNG image") from exc


def _png(image):
    out = BytesIO(); image.save(out, "PNG"); return out.getvalue()


def _trim_bounds(image):
    alpha_bounds = image.getchannel("A").getbbox()
    if alpha_bounds and alpha_bounds != (0, 0, image.width, image.height):
        return alpha_bounds
    background = Image.new("RGB", image.size, image.convert("RGB").getpixel((0, 0)))
    difference = ImageChops.difference(image.convert("RGB"), background).convert("L")
    # Ignore minor scanner noise while retaining document edges and ink.
    contents = difference.point(lambda value: 255 if value > 16 else 0).getbbox()
    return contents or (0, 0, image.width, image.height)


def _straighten_angle(image):
    pixels = np.asarray(image.convert("L"))
    edges = cv2.Canny(pixels, 50, 150)
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=max(50, image.width // 8),
        minLineLength=max(100, image.width // 5),
        maxLineGap=20,
    )
    if lines is None:
        return 0.0
    angles = []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        if angle > 45:
            angle -= 90
        elif angle < -45:
            angle += 90
        angles.append(angle)
    return round(-float(np.median(angles)), 1) if angles else 0.0


def _operation(kind, data, options):
    image = _image(data)
    if kind == "crop":
        x,y,w,h = (options[k] for k in ("x","y","width","height")); return image.crop((round(x*image.width), round(y*image.height), round((x+w)*image.width), round((y+h)*image.height)))
    if kind == "rotate":
        degrees = options["degrees"]
        return image if degrees == 0 else image.transpose({90:Image.Transpose.ROTATE_270,180:Image.Transpose.ROTATE_180,270:Image.Transpose.ROTATE_90}[degrees])
    if kind == "straighten": return image.rotate(-options["angle"], Image.Resampling.BICUBIC, expand=True, fillcolor=(0,0,0,0))
    if kind == "trim":
        l,r,t,b = options["left"],options["right"],options["top"],options["bottom"]
        if image.width-l-r <= 0 or image.height-t-b <= 0: raise ValueError("Region trim removes entire output")
        return image.crop((l,t,image.width-r,image.height-b))
    if kind == "remove_background":
        from rembg import new_session, remove
        return _image(remove(data, session=new_session(options["model"]), alpha_matting=options["alpha_matting"], alpha_matting_foreground_threshold=options["alpha_matting_foreground_threshold"], alpha_matting_background_threshold=options["alpha_matting_background_threshold"], alpha_matting_erode_size=options["alpha_matting_erode_size"], post_process_mask=options["post_process_mask"], force_return_bytes=True))
    raise ValueError("Unknown operation")


CATALOG = []
for kind in SCHEMAS:
    helpers = []
    if kind in ("straighten", "trim"):
        name = "auto_straighten" if kind == "straighten" else "auto_trim"
        helpers.append({"name":name,"schema_url":f"/operations/{kind}/helpers/{name}/schema.json","invoke_url":f"/operations/{kind}/helpers/{name}/invoke"})
    CATALOG.append({"kind":kind,"schema_url":f"/operations/{kind}/schema.json","render_url":f"/operations/{kind}/render","helpers":helpers})


@app.get("/health")
def health(): return {"status":"ok"}

@app.get("/operations")
def operations(): return {"operations": CATALOG}

@app.get("/operations/{kind}/schema.json")
def schema(kind: str):
    if kind not in SCHEMAS: raise HTTPException(404, "Unknown operation")
    return SCHEMAS[kind]

async def _options(raw: str, kind: str):
    try: return VALIDATORS[kind](json.loads(raw))
    except (KeyError, TypeError, json.JSONDecodeError, ValueError) as exc: raise HTTPException(422, {"code":"invalid_options","message":str(exc)})

@app.post("/operations/{kind}/render")
async def render(kind: str, options: str = Form(...), image: UploadFile = File(...), width: int | None = Form(None), height: int | None = Form(None)):
    if kind not in VALIDATORS: raise HTTPException(404, "Unknown operation")
    parsed = await _options(options, kind)
    try:
        result = _operation(kind, await image.read(), parsed)
    except ValueError as exc:
        raise HTTPException(422, {"code":"invalid_image","message":str(exc)}) from exc
    data = _png(result)
    return Response(data, media_type="image/png", headers={"X-Image-Width":str(result.width),"X-Image-Height":str(result.height)})

@app.get("/operations/{kind}/helpers/{helper}/schema.json")
def helper_schema(kind: str, helper: str):
    if (kind,helper) not in (("straighten","auto_straighten"),("trim","auto_trim")): raise HTTPException(404,"Unknown helper")
    return _schema("Auto-detect", {}, [], require_image=True)

@app.post("/operations/{kind}/helpers/{helper}/invoke")
async def invoke(kind: str, helper: str, invocation_options: str = Form(...), current_options: str = Form(...), image: UploadFile = File(...), width: int = Form(...), height: int = Form(...)):
    if (kind,helper) not in (("straighten","auto_straighten"),("trim","auto_trim")): raise HTTPException(404,"Unknown helper")
    try:
        current = json.loads(current_options); data = await image.read(); pil = _image(data)
        if kind == "trim":
            bbox = _trim_bounds(pil)
            x,y,r,b = bbox; result = {"top":y,"right":pil.width-r,"bottom":pil.height-b,"left":x}
        else: result = {**current, "angle": _straighten_angle(pil)}
        return {"options": VALIDATORS[kind](result)}
    except Exception as exc: raise HTTPException(422, {"code":"helper_failed","message":str(exc)})
