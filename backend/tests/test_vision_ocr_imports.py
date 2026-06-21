"""Tests for issue #591 — module-level OCR imports with a global ``HAS_OCR`` flag.

These verify that PIL/pytesseract are imported once at module load rather than
inline on every ``_ocr_caption`` call, and that the hot path short-circuits on
the boolean flag instead of re-running an import/try-except on each image.
"""
import builtins
import importlib
import inspect

from app.rag import vision


class _Boom:
    """Any attribute access raises — proves the OCR backend is never touched."""

    def __getattr__(self, _name):
        raise AssertionError(
            "OCR backend must not be accessed when HAS_OCR is False"
        )


def _fake_image(return_text):
    """Build a stand-in ``PIL.Image`` whose pipeline yields ``return_text``."""

    class _FakeImg:
        def convert(self, mode):
            assert mode == "RGB"
            return self

    return type("FakeImage", (), {"open": staticmethod(lambda _buf: _FakeImg())})


def _fake_pytesseract(return_text):
    return type(
        "FakePytesseract",
        (),
        {"image_to_string": staticmethod(lambda _img: return_text)},
    )


# ── Module surface ───────────────────────────────────────────────────────────

def test_module_exposes_boolean_has_ocr_flag():
    assert hasattr(vision, "HAS_OCR")
    assert isinstance(vision.HAS_OCR, bool)


def test_image_and_pytesseract_are_module_level_symbols():
    # Present as module globals regardless of availability (None when missing).
    assert "Image" in vars(vision)
    assert "pytesseract" in vars(vision)


def test_ocr_caption_has_no_inline_imports():
    """Regression guard: inline imports must not creep back into the hot path."""
    src = inspect.getsource(vision._ocr_caption)
    assert "import pytesseract" not in src
    assert "from PIL" not in src
    assert "HAS_OCR" in src  # the flag is what gates execution now


# ── Runtime behaviour ─────────────────────────────────────────────────────────

def test_ocr_caption_short_circuits_when_unavailable(monkeypatch):
    """HAS_OCR False → returns '' without ever touching Image/pytesseract."""
    monkeypatch.setattr(vision, "HAS_OCR", False)
    monkeypatch.setattr(vision, "Image", _Boom(), raising=False)
    monkeypatch.setattr(vision, "pytesseract", _Boom(), raising=False)
    assert vision._ocr_caption(b"any-bytes") == ""


def test_ocr_caption_uses_module_objects_when_available(monkeypatch):
    monkeypatch.setattr(vision, "HAS_OCR", True)
    monkeypatch.setattr(vision, "Image", _fake_image("  hello world  "))
    monkeypatch.setattr(vision, "pytesseract", _fake_pytesseract("  hello world  "))
    assert vision._ocr_caption(b"img-bytes") == "hello world"


def test_ocr_caption_truncates_long_text(monkeypatch):
    long_text = "x" * 600
    monkeypatch.setattr(vision, "HAS_OCR", True)
    monkeypatch.setattr(vision, "Image", _fake_image(long_text))
    monkeypatch.setattr(vision, "pytesseract", _fake_pytesseract(long_text))
    result = vision._ocr_caption(b"img")
    assert result.endswith("...")
    assert len(result) == 503  # 500 chars + "..."


def test_ocr_caption_swallows_runtime_errors(monkeypatch):
    """A pytesseract runtime error (e.g. missing tesseract binary) returns ''."""
    def _boom(_img):
        raise RuntimeError("tesseract is not installed or not in PATH")

    monkeypatch.setattr(vision, "HAS_OCR", True)
    monkeypatch.setattr(vision, "Image", _fake_image(""))
    monkeypatch.setattr(
        vision,
        "pytesseract",
        type("P", (), {"image_to_string": staticmethod(_boom)}),
    )
    assert vision._ocr_caption(b"img") == ""


# ── Import-availability detection ─────────────────────────────────────────────

def test_has_ocr_false_when_imports_missing(monkeypatch):
    """Reloading with PIL/pytesseract blocked sets HAS_OCR=False and leaves the
    backend symbols as None — and the hot path stays safe."""
    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "pytesseract" or name.split(".")[0] == "PIL":
            raise ImportError(f"blocked for test: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)
    reloaded = importlib.reload(vision)
    try:
        assert reloaded.HAS_OCR is False
        assert reloaded.Image is None
        assert reloaded.pytesseract is None
        assert reloaded._ocr_caption(b"bytes") == ""
    finally:
        # Restore real import machinery and the genuine module state so the
        # reloaded module object other tests share is left healthy.
        monkeypatch.undo()
        importlib.reload(reloaded)
