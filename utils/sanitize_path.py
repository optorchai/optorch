"""Path utilities for safe handling"""


def sanitize_path(*parts: str) -> str:
    """Sanitize and join path parts, handling slashes correctly
    
    Works for URLs, file paths, or any slash-separated paths.
    Removes duplicate slashes and handles leading/trailing slashes.
    
    Args:
        *parts: Path parts to sanitize and join
        
    Returns:
        Sanitized path
        
    Examples:
        sanitize("https://foo.com/mcp/", "/bar/") -> "https://foo.com/mcp/bar/"
        sanitize("/path/to/", "/file") -> "/path/to/file"
        sanitize("base", "middle", "end") -> "base/middle/end"
    """
    if not parts:
        return ""
    
    # Start with first part
    result = parts[0].rstrip('/')
    
    # Join remaining parts
    for part in parts[1:]:
        part = part.strip('/')
        if part:
            result = f"{result}/{part}"
    
    return result