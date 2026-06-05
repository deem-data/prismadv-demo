"""Unit tests for LLM factory functions."""

import os
from unittest.mock import patch

import pytest


def test_create_lm_from_env_openai():
    """Test factory with OpenAI API key."""
    dspy = pytest.importorskip("dspy")
    from prismadv.llm import create_lm_from_env

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}, clear=True):
        lm = create_lm_from_env(load_dotenv=False)
        assert lm is not None
        assert "gpt-4o-mini" in str(lm.model)


def test_create_lm_from_env_anthropic():
    """Test factory with Anthropic API key."""
    dspy = pytest.importorskip("dspy")
    from prismadv.llm import create_lm_from_env

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test123"}, clear=True):
        lm = create_lm_from_env(load_dotenv=False)
        assert lm is not None
        assert "claude" in str(lm.model).lower() or "haiku" in str(lm.model).lower()


def test_create_lm_from_env_gemini():
    """Test factory with Gemini API key."""
    dspy = pytest.importorskip("dspy")
    from prismadv.llm import create_lm_from_env

    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key-123"}, clear=True):
        lm = create_lm_from_env(load_dotenv=False)
        assert lm is not None
        assert "gemini" in str(lm.model).lower()


def test_create_lm_from_env_no_key():
    """Test factory raises error when no API key is found."""
    dspy = pytest.importorskip("dspy")
    from prismadv.llm import create_lm_from_env

    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="No LLM API key found"):
            create_lm_from_env(load_dotenv=False)


def test_create_lm_from_env_model_override():
    """Test factory with model override."""
    dspy = pytest.importorskip("dspy")
    from prismadv.llm import create_lm_from_env

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}, clear=True):
        lm = create_lm_from_env(model="openai/gpt-4o", load_dotenv=False)
        assert lm is not None
        assert "gpt-4o" in str(lm.model)


def test_create_lm_explicit():
    """Test explicit LM creation."""
    dspy = pytest.importorskip("dspy")
    from prismadv.llm import create_lm

    lm = create_lm("openai", api_key="sk-test123", model="openai/gpt-4o")
    assert lm is not None
    assert "gpt-4o" in str(lm.model)


def test_create_lm_invalid_provider():
    """Test explicit LM creation with invalid provider."""
    dspy = pytest.importorskip("dspy")
    from prismadv.llm import create_lm

    with pytest.raises(ValueError, match="Invalid provider"):
        create_lm("invalid", api_key="test")
