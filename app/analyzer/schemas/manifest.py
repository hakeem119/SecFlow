from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class BaseManifestModel(BaseModel):
    """Base model enforcing no extra fields."""
    model_config = ConfigDict(extra="allow")


class EvidenceItem(BaseManifestModel):
    """Evidence structure mapping claims back to source file lines."""
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    description: str


class DependencyItem(BaseManifestModel):
    """Key library/package dependency with exact version information."""
    name: str
    version: Optional[str] = None  # e.g., "^4.17.21", "2.0.1"
    is_dev: bool = False
    description: Optional[str] = None


class SecretItem(BaseManifestModel):
    """Detected secrets, tokens, credentials, or sensitive configurations."""
    name: str  # e.g., "JWT_SECRET", "DB_PASSWORD"
    type: Literal["env_var", "hardcoded_fallback", "config_file", "secret_manager", "other"]
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    description: str


class ApiEndpoint(BaseManifestModel):
    """Discovered API routes, endpoints, or socket channels with parameter/auth details."""
    path: str  # e.g., "/api/v1/users/upload-avatar"
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD", "WS"]
    auth_required: bool = False
    auth_method: Optional[Literal["jwt", "session_cookie", "api_key", "oauth2", "basic", "none", "custom"]] = None
    middlewares: List[str] = Field(default_factory=list)  # e.g., ["authGuard", "uploadMiddleware", "rateLimiter"]
    input_types: List[Literal["query", "path_param", "json_body", "form_data", "file_upload", "header", "none"]] = Field(default_factory=list)
    response_type: Optional[str] = "application/json"  # e.g., "application/json", "text/html", "file_stream"
    description: Optional[str] = None


class MiddlewareItem(BaseManifestModel):
    """Identified middleware components and security filters."""
    name: str  # e.g., "jwtVerify", "cors", "helmet"
    type: Literal["auth", "cors", "rate_limit", "logging", "validation", "security_headers", "file_handling", "error_handling", "other"]
    description: str
    file_path: Optional[str] = None


class Technology(BaseManifestModel):
    """Detected technology component."""
    name: str
    category: Literal[
        "language", "framework", "database", "orm", 
        "library", "tool", "ci_cd", "runtime"
    ]
    version: Optional[str] = None
    evidence: List[EvidenceItem]


class ProjectMetadata(BaseManifestModel):
    """Core metadata about the repository."""
    name: str
    type: Literal[
        "web_application", "api_service", "cli_tool", 
        "library", "microservice", "monolith"
    ]
    description: str
    primary_purpose: str


class Actor(BaseManifestModel):
    """Identified system actors, personas, and privilege tiers."""
    name: str
    role: str


class Architecture(BaseManifestModel):
    """Architectural patterns, entry points, and components."""
    pattern: Literal[
        "monolith", "microservices", "modular_monolith", 
        "event_driven", "serverless", "unknown"
    ]
    entry_points: List[str]
    core_components: List[str]
    global_middlewares: List[MiddlewareItem] = Field(default_factory=list)
    data_flow_summary: str


class Deployment(BaseManifestModel):
    """Deployment targets and containerization info."""
    containerized: bool
    configs: List[str]
    target_platforms: List[str]


class ProjectManifest(BaseManifestModel):
    """Root model AI Analyzer output."""
    project: ProjectMetadata
    actors: List[Actor]
    technologies: List[Technology]
    architecture: Architecture
    deployment: Deployment
    key_dependencies: List[DependencyItem] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    evidence_ledger: List[EvidenceItem]
    secrets: List[SecretItem] = Field(default_factory=list)
    endpoints: List[ApiEndpoint] = Field(default_factory=list)