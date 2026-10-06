"""
Shared limit constants.
These bounds define the absolute maximums for the system and are used as
both the upper limits in configuration (Settings) and the maximum list lengths
in schemas (e.g. RepositorySnapshot) to prevent memory exhaustion.
"""

LIMIT_TTL_HOURS_MAX = 720
LIMIT_MAX_FILE_SIZE_BYTES = 100_000_000
LIMIT_MAX_FILE_COUNT = 100_000
LIMIT_MAX_TOTAL_SIZE_BYTES = 10_000_000_000
LIMIT_TOOL_TIMEOUT_SECONDS_MAX = 3600
LIMIT_MAX_DIRECTORY_DEPTH = 64

# Limits applied to lists in the snapshot schema and output parsing
LIMIT_MAX_OUTPUT_ITEMS = 100_000

# Security: Maximum request body size in bytes to prevent memory exhaustion
LIMIT_MAX_REQUEST_BODY_BYTES = 4096
