"""
Configuration classes for the LangGraph agentic pipeline.
"""

from pydantic import BaseModel, Field
from typing import Optional
from core.config import DENSE_RESULT_WEIGHT, SPARSE_RESULT_WEIGHT


class RetrievalConfig(BaseModel):
    """Configuration for document retrieval."""
    
    shia_doc_count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of Shia documents to retrieve"
    )
    
    sunni_doc_count: int = Field(
        default=2,
        ge=0,
        le=20,
        description="Number of Sunni documents to retrieve"
    )
    
    reranking_enabled: bool = Field(
        default=True,
        description="Whether to use reranking for retrieved documents"
    )
    
    dense_weight: float = Field(
        default=float(DENSE_RESULT_WEIGHT),
        ge=0.0,
        le=1.0,
        description="Weight for dense retrieval results"
    )
    
    sparse_weight: float = Field(
        default=float(SPARSE_RESULT_WEIGHT),
        ge=0.0,
        le=1.0,
        description="Weight for sparse retrieval results"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "shia_doc_count": 5,
                "sunni_doc_count": 2,
                "reranking_enabled": True,
                "dense_weight": 0.8,
                "sparse_weight": 0.2
            }
        }


class ModelConfig(BaseModel):
    """Configuration for LLM models."""
    
    agent_model: str = Field(
        default="gpt-4o",
        description="Model to use for the agent (tool calling)"
    )
    
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for response generation"
    )
    
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum tokens for response generation"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_model": "gpt-4o",
                "temperature": 0.7,
                "max_tokens": 2000
            }
        }


class AgentConfig(BaseModel):
    """Complete configuration for the agentic chat pipeline."""
    
    retrieval: RetrievalConfig = Field(
        default_factory=RetrievalConfig,
        description="Retrieval configuration"
    )
    
    model: ModelConfig = Field(
        default_factory=ModelConfig,
        description="Model configuration"
    )
    
    max_iterations: int = Field(
        default=15,
        ge=1,
        le=50,
        description="Maximum number of agent iterations"
    )
    
    enable_classification: bool = Field(
        default=True,
        description="Whether to enable query classification (non-Islamic/fiqh detection)"
    )
    
    enable_translation: bool = Field(
        default=True,
        description="Whether to enable automatic translation"
    )
    
    enable_enhancement: bool = Field(
        default=True,
        description="Whether to enable query enhancement"
    )
    
    stream_intermediate_steps: bool = Field(
        default=False,
        description="Whether to stream tool calls and intermediate steps"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "retrieval": {
                    "shia_doc_count": 5,
                    "sunni_doc_count": 2
                },
                "model": {
                    "agent_model": "gpt-4o",
                    "temperature": 0.7
                },
                "max_iterations": 15,
                "enable_classification": True,
                "enable_translation": True,
                "enable_enhancement": True,
                "stream_intermediate_steps": False
            }
        }
    
    def to_dict(self):
        """Convert config to dictionary for storage in state."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        """Create config from dictionary."""
        return cls(**data)


# Default configuration instance
DEFAULT_AGENT_CONFIG = AgentConfig()





