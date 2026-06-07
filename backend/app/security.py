# Create this new file or append to your existing helpers
from pathlib import Path
from fastapi import HTTPException, status

def verify_secure_sandbox_path(filename: str, sandbox_base_dir: str) -> Path:
    """
    Validates that a requested filename stays strictly within the sandbox directory.
    Raises a clean 403 Forbidden error if a path traversal attempt is detected.
    """
    base_path = Path(sandbox_base_dir).resolve()
    target_path = (base_path / filename).resolve()
    
    if not target_path.is_relative_to(base_path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Invalid resource path mapping."
        )
        
    return target_path
