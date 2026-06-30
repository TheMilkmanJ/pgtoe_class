"""
Safe file access module for reading PolyChord-locked files.

This module provides non-blocking file access that works even when
PolyChord has files locked during sampling stages.
"""

import os
import sys
import time
import shutil
import tempfile
from pathlib import Path
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def _non_blocking_read(file_path) -> Tuple[Optional[str], bool]:
    """
    Attempt non-blocking read of a file.
    
    On Linux/Unix systems, uses O_NONBLOCK flag to avoid blocking on locked files.
    On other systems, falls back to regular file reading.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        Tuple of (content as string, success: bool)
    """
    try:
        file_path = str(file_path)
        
        # Use low-level OS open with O_NONBLOCK flag (Linux/Unix)
        if hasattr(os, 'O_NONBLOCK'):
            fd = os.open(file_path, os.O_RDONLY | os.O_NONBLOCK)
            try:
                file_size = os.path.getsize(file_path)
                content = os.read(fd, file_size).decode('utf-8', errors='replace')
                return content, True
            finally:
                os.close(fd)
        else:
            # Windows or systems without O_NONBLOCK
            with open(file_path, 'r') as f:
                return f.read(), True
    except (BlockingIOError, IOError, OSError, PermissionError, FileNotFoundError) as e:
        logger.debug(f"Non-blocking read failed for {file_path}: {e}")
        return None, False
    except Exception as e:
        logger.warning(f"Unexpected error reading {file_path}: {e}")
        return None, False


def _copy_then_read(file_path) -> Tuple[Optional[str], bool]:
    """
    Copy-then-read pattern to avoid blocking on locked files.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        Tuple of (content as string, success: bool)
    """
    try:
        file_path = str(file_path)
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.tmp', delete=True) as tmp:
            try:
                # Use shutil.copy2 which preserves metadata
                shutil.copy2(file_path, tmp.name)
                
                # Now read the temp file
                tmp.seek(0)
                content = tmp.read()
                return content, True
            except (IOError, OSError, PermissionError) as e:
                logger.debug(f"Copy failed for {file_path}: {e}")
                return None, False
    except Exception as e:
        logger.warning(f"Copy-then-read failed for {file_path}: {e}")
        return None, False


def read_file_safely(file_path, max_retries: int = 5, retry_delay: float = 0.1) -> Tuple[Optional[str], bool]:
    """
    Read a file safely with retry logic for file access conflicts.
    
    Uses multiple strategies to avoid blocking on files that may be
    locked by PolyChord during active sampling stages:
    
    1. Non-blocking direct read (fastest, works on Linux with O_NONBLOCK)
    2. Copy-then-read pattern (works on most systems)
    3. Retry with exponential backoff
    
    This function is designed to work even when PolyChord has files
    locked with exclusive locks during sampling.
    
    Args:
        file_path: Path to the file to read
        max_retries: Maximum number of retry attempts (default: 5)
        retry_delay: Base delay between retries in seconds (default: 0.1)
        
    Returns:
        Tuple of (file contents as string, success: bool)
        
    Example:
        >>> content, success = read_file_safely("chains/prtoe_poly.stats")
        >>> if success:
        ...     print(f"Read {len(content)} bytes")
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.debug(f"File does not exist: {file_path}")
        return None, False
    
    if file_path.stat().st_size == 0:
        logger.debug(f"File is empty: {file_path}")
        return "", True
    
    for attempt in range(max_retries):
        # Strategy 1: Non-blocking direct read (fastest)
        content, success = _non_blocking_read(file_path)
        if success:
            logger.debug(f"Non-blocking read succeeded for {file_path} (attempt {attempt + 1})")
            return content, True
        
        # Strategy 2: Copy-then-read pattern
        content, success = _copy_then_read(file_path)
        if success:
            logger.debug(f"Copy-then-read succeeded for {file_path} (attempt {attempt + 1})")
            return content, True
        
        # Exponential backoff: wait longer on each retry
        if attempt < max_retries - 1:
            sleep_time = retry_delay * (2 ** attempt)  # 0.1s, 0.2s, 0.4s, 0.8s, 1.6s...
            logger.debug(f"Retry {attempt + 1}/{max_retries} for {file_path}, waiting {sleep_time:.2f}s")
            time.sleep(sleep_time)
    
    # Final fallback attempt
    logger.warning(f"All retry attempts failed for {file_path}, trying final non-blocking read")
    content, success = _non_blocking_read(file_path)
    if success:
        return content, True
    
    logger.error(f"Failed to read file after {max_retries} attempts: {file_path}")
    return None, False


def read_file_with_fallback(file_path, fallback_paths=None, max_retries: int = 5) -> Tuple[Optional[str], bool]:
    """
    Read a file with fallback paths if the main file is not accessible.
    
    This is useful for PolyChord files that might be in different locations
    depending on the configuration (e.g., in _polychord_raw subdirectory).
    
    Args:
        file_path: Primary path to the file to read
        fallback_paths: List of alternative paths to try if primary fails
        max_retries: Maximum number of retry attempts per path
        
    Returns:
        Tuple of (file contents as string, success: bool)
    """
    paths_to_try = [file_path]
    if fallback_paths:
        paths_to_try.extend(fallback_paths)
    
    for path in paths_to_try:
        content, success = read_file_safely(path, max_retries)
        if success:
            return content, True
    
    return None, False


def read_stats_file(output_prefix) -> Tuple[Optional[dict], bool]:
    """
    Read a PolyChord stats file safely, trying multiple locations.
    
    PolyChord can write stats files in different locations:
    - {prefix}.stats
    - {prefix}_polychord_raw/{prefix}.stats
    
    Args:
        output_prefix: The output prefix (e.g., "chains/prtoe_poly")
        
    Returns:
        Tuple of (parsed stats dict, success: bool)
    """
    import json
    from prtoe_class.backend.parsers_adapter import parse_polychord_stats
    
    prefix = Path(output_prefix)
    
    # Try primary location
    stats_file = prefix.with_suffix(".stats")
    content, success = read_file_safely(stats_file)
    if success and content:
        try:
            # Try to parse as JSON first
            return json.loads(content), True
        except (json.JSONDecodeError, ValueError):
            # Try using the parser adapter
            result = parse_polychord_stats(stats_file, None)
            if result:
                return result, True
    
    # Try alternative location (PolyChord raw directory)
    raw_stats_file = prefix.parent / f"{prefix.name}_polychord_raw" / f"{prefix.name}.stats"
    content, success = read_file_safely(raw_stats_file)
    if success and content:
        try:
            return json.loads(content), True
        except (json.JSONDecodeError, ValueError):
            result = parse_polychord_stats(raw_stats_file, None)
            if result:
                return result, True
    
    return None, False


def read_live_file(output_prefix) -> Tuple[Optional[str], bool]:
    """
    Read a PolyChord live file safely.
    
    Args:
        output_prefix: The output prefix
        
    Returns:
        Tuple of (file contents as string, success: bool)
    """
    prefix = Path(output_prefix)
    
    # Try primary location
    live_file = prefix.parent / f"{prefix.name}_polychord_raw" / f"{prefix.name}_phys_live.txt"
    content, success = read_file_safely(live_file)
    if success:
        return content, True
    
    return None, False


if __name__ == "__main__":
    # Test the module
    import tempfile
    import subprocess
    
    print("Testing safe file access module...")
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.test', delete=False) as f:
        f.write("test content\n")
        test_file = f.name
    
    print(f"Created test file: {test_file}")
    
    # Test reading
    content, success = read_file_safely(test_file)
    print(f"Read test: success={success}, content length={len(content) if content else 0}")
    
    # Clean up
    os.unlink(test_file)
    print("Test completed.")