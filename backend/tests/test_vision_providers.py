"""Tests for the VLM provider Strategy Pattern (issue #592)."""
from unittest.mock import MagicMock, patch
import pytest

from app.vision.base import BaseVisionProvider
from app.vision.registry import _REGISTRY, get_vision_provider, register_provider


class TestBaseVisionProvider:
    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            BaseVisionProvider()

    def test_concrete_subclass_works(self):
        class Dummy(BaseVisionProvider):
            def caption(self, image_bytes: bytes) -> str:
                return "dummy"
        assert Dummy().caption(b"x") == "dummy"


class TestRegistry:
    def setup_method(self):
        self._original = dict(_REGISTRY)

    def teardown_method(self):
        _REGISTRY.clear()
        _REGISTRY.update(self._original)

    def test_register_and_retrieve(self):
        class FakeProvider(BaseVisionProvider):
            def caption(self, image_bytes: bytes) -> str:
                return "fake"
        register_provider("fake", FakeProvider)
        assert get_vision_provider("fake") is not None

    def test_case_insensitive(self):
        class P(BaseVisionProvider):
            def caption(self, image_bytes: bytes) -> str:
                return ""
        register_provider("UPPER", P)
        assert get_vision_provider("upper") is not None

    def test_unknown_returns_none(self):
        assert get_vision_provider("doesnotexist") is None

    def test_none_returns_none(self):
        assert get_vision_provider(None) is None

    def test_broken_init_returns_none(self):
        class Broken(BaseVisionProvider):
            def __init__(self): raise RuntimeError("fail")
            def caption(self, image_bytes: bytes) -> str: return ""
        register_provider("broken", Broken)
        assert get_vision_provider("broken") is None


class TestCaptionImage:
    def test_uses_provider_when_configured(self):
        from app.rag.vision import caption_image

        class StubProvider(BaseVisionProvider):
            def caption(self, image_bytes: bytes) -> str:
                return "stub caption"

        with patch("app.rag.vision.get_vision_provider", return_value=StubProvider()):
            assert caption_image(b"img", page=1) == "stub caption"

    def test_falls_back_to_ocr(self):
        from app.rag.vision import caption_image

        class EmptyProvider(BaseVisionProvider):
            def caption(self, image_bytes: bytes) -> str:
                return ""

        with patch("app.rag.vision.get_vision_provider", return_value=EmptyProvider()):
            with patch("app.rag.vision._ocr_caption", return_value="ocr text"):
                assert caption_image(b"img", page=1) == "ocr text"

    def test_falls_back_to_placeholder(self):
        from app.rag.vision import caption_image

        with patch("app.rag.vision.get_vision_provider", return_value=None):
            with patch("app.rag.vision._ocr_caption", return_value=""):
                result = caption_image(b"img", page=3)
        assert "page 3" in result

    def test_batch_mode(self):
        from app.rag.vision import caption_image

        with patch("app.rag.vision.get_vision_provider", return_value=None):
            with patch("app.rag.vision._ocr_caption", return_value=""):
                results = caption_image([b"img1", b"img2"], page=[1, 2])
        assert isinstance(results, list) and len(results) == 2