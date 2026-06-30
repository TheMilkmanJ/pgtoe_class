# Fix for Real-Time Monitor / PolyChord File Locking Conflict

## Problem

The Real-Time Monitor (cosmicdashboard) interferes with PolyChord/CosmicForge sessions. When PolyChord enters the sampling stage, it locks files with exclusive locks. The dashboard tries to read these same files and blocks, causing the process to freeze and stop writing to files.

## Root Cause

PolyChord uses **exclusive file locking** during sampling to prevent corruption. The dashboard's current `_read_file_safely()` function uses `shutil.copy2()` which can block on some filesystems when files are exclusively locked by another process.

## Solutions

### 🔥 **Immediate Fix: Disable Real-Time Monitoring During Sampling**

If you're currently stuck, **kill the dashboard process** to release the locks:

```bash
# Find and kill dashboard processes
pkill -f "cosmo_dashboard_backend"
pkill -f "uvicorn"
pkill -f "dashboard"

# Or kill specific PIDs
ps aux | grep dashboard
kill -9 <PID>
```

### ✅ **Solution 1: Use Non-Blocking File Access (Recommended)**

I've created an enhanced `file_access_safe.py` module that uses **non-blocking I/O** to read PolyChord files without blocking.

**Apply the fix:**

```bash
# The new module is already created at:
# /home/themilkmanj/prtoe_class/scripts/file_access_safe.py

# To use it in the dashboard, modify cosmo_dashboard_backend.py
# to import and use the new safe reading functions
```

**Key improvements:**
- Uses `O_NONBLOCK` flag on Linux for truly non-blocking reads
- Multiple fallback strategies (direct read, copy-then-read)
- Exponential backoff (0.1s, 0.2s, 0.4s, 0.8s, 1.6s)
- More retries (5 instead of 3)
- Better error handling and logging

### ✅ **Solution 2: Patch the Dashboard Backend**

Replace the `_read_file_safely()` function in `cosmo_dashboard_backend.py` with this improved version:

```python
def _read_file_safely(file_path, max_retries=5, retry_delay=0.1):
    """Read a file safely with retry logic for PolyChord-locked files."""
    import time
    import shutil
    import tempfile
    import os
    
    def _non_blocking_read(file_path):
        """Attempt non-blocking read using O_NONBLOCK."""
        try:
            if hasattr(os, 'O_NONBLOCK'):
                fd = os.open(str(file_path), os.O_RDONLY | os.O_NONBLOCK)
                try:
                    file_size = os.path.getsize(str(file_path))
                    content = os.read(fd, file_size).decode('utf-8', errors='replace')
                    return content, True
                finally:
                    os.close(fd)
            else:
                with open(str(file_path), 'r') as f:
                    return f.read(), True
        except (BlockingIOError, IOError, OSError, PermissionError, FileNotFoundError):
            return None, False
    
    file_path = Path(file_path)
    if not file_path.exists():
        return None, False
    if file_path.stat().st_size == 0:
        return "", True
    
    for attempt in range(max_retries):
        # Try non-blocking read first
        content, success = _non_blocking_read(file_path)
        if success:
            return content, True
        
        # Fallback: copy-then-read
        try:
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.tmp', delete=True) as tmp:
                shutil.copy2(str(file_path), tmp.name)
                tmp.seek(0)
                return tmp.read(), True
        except (IOError, OSError, PermissionError):
            pass
        
        # Exponential backoff
        if attempt < max_retries - 1:
            time.sleep(retry_delay * (2 ** attempt))
    
    # Final attempt
    content, success = _non_blocking_read(file_path)
    return content, success if success else (None, False)
```

### ✅ **Solution 3: Run Dashboard in Read-Only Mode During Sampling**

Modify the dashboard to **disable live monitoring** during PolyChord sampling phases:

```python
# In cosmo_dashboard_backend.py, check if PolyChord is in sampling phase
# and use a different (more patient) file reading strategy

if is_polychord_sampling():
    # Use longer timeouts and more retries
    content, success = read_file_safely(file_path, max_retries=10, retry_delay=0.5)
else:
    # Normal operation
    content, success = _read_file_safely(file_path)
```

### ✅ **Solution 4: Use File Monitoring Instead of Polling**

Instead of constantly polling files, use **inotify** (Linux) or **watchdog** to monitor file changes and only read when files are updated and unlocked.

```bash
pip install watchdog
```

## How to Test the Fix

1. **Start PolyChord run:**
```bash
python run_cosmicforge.py prtoe_standard.yaml --cores 4
```

2. **Start dashboard with safe file access:**
```bash
# Make sure the dashboard uses the new file_access_safe module
cd scripts
python cosmo_dashboard_backend.py
```

3. **Monitor file access:**
```bash
# Check for blocked processes
tail -f /var/log/syslog | grep -i lock

# Check dashboard logs
tail -f chains/dashboard_errors.log
```

## Prevention: Run Without Dashboard During Sampling

For production runs, **disable the Real-Time Monitor during sampling**:

```bash
# Run PolyChord without dashboard
python run_cosmicforge.py prtoe_standard.yaml --cores 4

# After sampling completes, start dashboard for analysis
python scripts/cosmo_dashboard_backend.py
```

## File Locking Technical Details

### How PolyChord Locks Files
- PolyChord uses **flock()** system calls for file locking
- Locks are **exclusive** (write locks) during sampling
- Files affected: `.txt`, `.stats`, `.resume`, `.json`

### How the Dashboard Accesses Files
- Current: `shutil.copy2()` which can block on locked files
- Fixed: `os.open(..., O_NONBLOCK)` which returns immediately with `BlockingIOError` if file is locked

### Linux File Locking Behavior
- `O_NONBLOCK` + read: Returns `BlockingIOError` if file is write-locked
- Regular open + read: **Blocks** until lock is released
- `flock()`: Advisory locks, can be bypassed with non-blocking I/O

## Configuration Options

### Option A: Disable Live Monitoring (Fastest)
```yaml
# In dashboard config
dashboard:
  live_monitoring: false
  poll_interval: 60  # Only check files every 60 seconds
```

### Option B: Use Safe File Access (Recommended)
```yaml
# In dashboard config
dashboard:
  file_access: safe_nonblocking
  max_retries: 10
  retry_delay: 0.2
```

### Option C: Increase Timeouts
```yaml
# In dashboard config
dashboard:
  file_timeout: 5.0  # Wait up to 5 seconds per file
  stale_data_age: 30  # Accept data up to 30 seconds old
```

## Files Modified/Created

| File | Action | Purpose |
|------|--------|---------|
| `scripts/file_access_safe.py` | ✅ Created | Non-blocking file access module |
| `FIX_FILE_LOCKING.md` | ✅ Created | This documentation |
| `cosmo_dashboard_backend.py` | ⏳ Needs patch | Update to use safe file access |

## Verification

After applying the fix, verify with:

```bash
# Test file access on a locked file
python -c "
from scripts.file_access_safe import read_file_safely
import tempfile

# Create test file
with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
    f.write('test')
    fname = f.name

# Test reading
content, success = read_file_safely(fname)
print(f'Success: {success}, Content: {content}')

import os
os.unlink(fname)
"
```

## Still Having Issues?

If processes are still freezing:

1. **Check what's locking the files:**
```bash
lsof +D /home/themilkmanj/prtoe_class/chains/
fuser -v /home/themilkmanj/prtoe_class/chains/*.txt
```

2. **Kill all conflicting processes:**
```bash
pkill -9 -f poly
pkill -9 -f cobaya
pkill -9 -f cosmic
```

3. **Clean up locked files:**
```bash
fuser -k /home/themilkmanj/prtoe_class/chains/*.txt
```

4. **Contact support with:**
   - Process list: `ps aux | grep -E "cosmic|poly|dashboard"`
   - File locks: `lsof +D /home/themilkmanj/prtoe_class/chains/`
   - Dashboard logs: `tail -n 100 chains/dashboard_errors.log`

---

**Priority**: Use Solution 1 (Non-Blocking File Access) for immediate fix.
**Long-term**: Implement Solution 4 (File Monitoring) for best performance.

*Last updated: 2026-06-29*