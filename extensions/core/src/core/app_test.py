from io import BytesIO
import json

from fastapi.testclient import TestClient
from PIL import Image

from core.app import app


def _png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (4, 3), "white").save(output, "PNG")
    return output.getvalue()


def _rgba_png(size: tuple[int, int], color=(255, 0, 0, 255)) -> bytes:
    output = BytesIO()
    Image.new("RGBA", size, color).save(output, "PNG")
    return output.getvalue()


def _render(kind: str, options: dict, image: bytes) -> object:
    return TestClient(app).post(
        f"/operations/{kind}/render",
        data={"options": json.dumps(options)},
        files={"image": ("image.png", image, "image/png")},
    )


def test_render_schema_requires_image_and_endpoint_requires_image() -> None:
    client = TestClient(app)

    schema = client.get("/operations/rotate/schema.json")
    assert schema.status_code == 200
    assert schema.json()["x-hint-require-image"] is True

    response = client.post(
        "/operations/rotate/render",
        data={"options": '{"degrees": 90}'},
    )
    assert response.status_code == 422
    assert any(error["loc"][-1] == "image" for error in response.json()["detail"])


def test_render_rejects_invalid_image_as_contract_error() -> None:
    response = TestClient(app).post(
        "/operations/rotate/render",
        data={"options": '{"degrees": 90}'},
        files={"image": ("image.png", b"not an image", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_image"


def test_render_returns_png_and_dimensions() -> None:
    response = TestClient(app).post(
        "/operations/rotate/render",
        data={"options": '{"degrees": 90}'},
        files={"image": ("image.png", _png(), "image/png")},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-image-width"] == "3"
    assert response.headers["x-image-height"] == "4"


def test_crop_validates_rectangle_and_renders_dimensions() -> None:
    response = _render("crop", {"x": 0.25, "y": 0.1, "width": 0.5, "height": 0.75}, _rgba_png((100, 100)))
    assert response.status_code == 200
    assert (response.headers["x-image-width"], response.headers["x-image-height"]) == ("50", "75")

    response = _render("crop", {"x": 0.25, "y": 0.1, "width": 1, "height": 1}, _rgba_png((100, 100)))
    assert (response.headers["x-image-width"], response.headers["x-image-height"]) == ("75", "90")

    invalid = _render("crop", {"x": -0.1, "y": 0, "width": 1, "height": 1}, _png())
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "invalid_options"


def test_crop_boundary_normalized_values_render_non_empty_output() -> None:
    response = _render("crop", {"x": 0.999, "y": 0.999, "width": 1, "height": 1}, _rgba_png((100, 100)))
    assert response.status_code == 200
    assert (response.headers["x-image-width"], response.headers["x-image-height"]) == ("1", "1")


def test_crop_rejects_non_finite_and_non_real_values() -> None:
    for value in (True, "0.1", None):
        options = {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5}
        options["x"] = value
        assert _render("crop", options, _png()).status_code == 422


def test_rotate_validates_quarter_turns_and_swaps_dimensions() -> None:
    assert _render("rotate", {"degrees": 90}, _rgba_png((4, 3))).headers["x-image-width"] == "3"
    assert _render("rotate", {"degrees": 90}, _rgba_png((4, 3))).headers["x-image-height"] == "4"
    assert _render("rotate", {"degrees": 360}, _rgba_png((4, 3))).headers["x-image-width"] == "4"
    assert _render("rotate", {"degrees": 45}, _png()).status_code == 422
    assert _render("rotate", {"degrees": True}, _png()).status_code == 422


def test_straighten_validates_angle_and_renders_expanded_image() -> None:
    assert _render("straighten", {"angle": 0}, _rgba_png((4, 3))).headers["x-image-width"] == "4"
    response = _render("straighten", {"angle": 45}, _rgba_png((4, 3)))
    assert response.status_code == 200
    assert int(response.headers["x-image-width"]) > 4
    assert _render("straighten", {"angle": 46}, _png()).status_code == 422


def test_trim_validates_edges_and_renders_dimensions() -> None:
    options = {"top": 1, "right": 2, "bottom": 3, "left": 4}
    response = _render("trim", options, _rgba_png((10, 10)))
    assert (response.headers["x-image-width"], response.headers["x-image-height"]) == ("4", "6")
    assert _render("trim", {**options, "top": -1}, _png()).status_code == 422
    assert _render("trim", {**options, "top": True}, _png()).status_code == 422
    assert _render("trim", {"top": 10, "right": 0, "bottom": 0, "left": 0}, _png()).status_code == 422


def test_remove_background_validates_defaults_and_options() -> None:
    schema = TestClient(app).get("/operations/remove_background/schema.json")
    assert schema.status_code == 200
    assert schema.json()["properties"]["model"]["default"] == "birefnet-general"
    response = _render("remove_background", {"model": "unknown"}, _png())
    assert response.status_code == 422
    response = _render("remove_background", {"alpha_matting": "yes"}, _png())
    assert response.status_code == 422


def test_helpers_expose_straighten_and_trim_and_auto_trim_detects_transparent_and_opaque_margins() -> None:
    client = TestClient(app)
    assert client.get("/operations/straighten/helpers/auto_straighten/schema.json").status_code == 200
    assert client.get("/operations/trim/helpers/auto_trim/schema.json").status_code == 200
    image = _rgba_png((10, 10), (0, 0, 0, 0))
    with Image.open(BytesIO(image)) as source:
        source.putpixel((2, 3), (255, 0, 0, 255))
        output = BytesIO()
        source.save(output, "PNG")
    response = client.post(
        "/operations/trim/helpers/auto_trim/invoke",
        data={"invocation_options": "{}", "current_options": json.dumps({"top": 0, "right": 0, "bottom": 0, "left": 0}), "width": 10, "height": 10},
        files={"image": ("image.png", output.getvalue(), "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["options"] == {"top": 3, "right": 7, "bottom": 6, "left": 2}
    document = Image.new("RGB", (10, 10), "white")
    for x in range(2, 8):
        for y in range(3, 7):
            document.putpixel((x, y), (0, 0, 0))
    output = BytesIO()
    document.save(output, "PNG")
    response = client.post(
        "/operations/trim/helpers/auto_trim/invoke",
        data={"invocation_options": "{}", "current_options": json.dumps({"top": 0, "right": 0, "bottom": 0, "left": 0}), "width": 10, "height": 10},
        files={"image": ("image.png", output.getvalue(), "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["options"] == {"top": 3, "right": 2, "bottom": 3, "left": 2}
