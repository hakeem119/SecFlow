from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

class BaseManifestModel(BaseModel):
    """Base model enforcing no extra fields."""
    model_config = ConfigDict(extra="forbid")

class EvidenceItem(BaseManifestModel):
    """Evidence structure mapping claims back to source file lines."""
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    description: str

class Technology(BaseManifestModel):
    """Detected technology component."""
    name: str
    category: Literal["language", "framework", "database", "orm", "library", "tool", "ci_cd", "runtime"]
    version: Optional[str] = None
    evidence: List[EvidenceItem]

class ProjectMetadata(BaseManifestModel):
    """Core metadata about the repository."""
    name: str
    type: Literal["web_application", "api_service", "cli_tool", "library", "microservice", "monolith"]
    description: str
    primary_purpose: str

class Actor(BaseManifestModel):
    """Identified system actors and roles."""
    name: str
    role: str

class Architecture(BaseManifestModel):
    """Architectural patterns and components."""
    pattern: Literal["monolith", "microservices", "modular_monolith", "event_driven", "serverless", "unknown"]
    entry_points: List[str]
    core_components: List[str]
    data_flow_summary: str

class Deployment(BaseManifestModel):
    """Deployment targets and containerization info."""
    containerized: bool
    configs: List[str]
    target_platforms: List[str]

class ProjectManifest(BaseManifestModel):
    """Root model for Team 2's AI Analyzer output."""
    project: ProjectMetadata
    actors: List[Actor]
    technologies: List[Technology]
    architecture: Architecture
    deployment: Deployment
    key_dependencies: List[str]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    evidence_ledger: List[EvidenceItem]
