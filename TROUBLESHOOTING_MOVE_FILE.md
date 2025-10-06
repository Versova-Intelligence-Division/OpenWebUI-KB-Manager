# 🔴 CRITICAL: move-file Command - Now COPY Only!

## 🚨 CRITICAL DISCOVERY

**OpenWebUI's `/knowledge/{id}/file/remove` API endpoint DELETES files entirely, not just removes the association!**

This has forced a complete redesign of the move-file command to prevent data loss.

## What Changed

The `move-file` command has been **completely redesigned** and now:
- **COPIES files** to the destination KB
- **LEAVES files** in the source KB  
- **NEVER removes files** from any KB

This is the ONLY safe approach given how OpenWebUI's API works.

## What Was Done

### Safety Improvements Added

1. **Pre-flight KB Verification**
   - The command now verifies that both source and destination KBs exist before attempting any operations
   - This prevents orphaned files and provides clear error messages if a KB doesn't exist

2. **Better Error Messages**
   - Specific errors for non-existent KBs
   - Warnings if a file is orphaned (removed from source but can't be added to destination)
   - Step-by-step progress indicators showing each operation

3. **Skip Verification Option**
   - Added `--skip-verify` flag for cases where verification might be causing issues
   - Not recommended for normal use, but useful for debugging

### Updated Command Syntax
```bash
# Standard usage with safety checks (recommended)
kb-manager move-file <file-id> <dest-kb-id> --from-kb <source-kb-id>

# Skip verification (use only for troubleshooting)
kb-manager move-file <file-id> <dest-kb-id> --from-kb <source-kb-id> --skip-verify
```

## Investigating the Crash

### Possible Causes

1. **Backend Bug in OpenWebUI**
   - The instance crash (502 error) suggests the OpenWebUI backend itself crashed
   - This is more likely a backend issue than a client issue
   - The timing could be coincidental

2. **Invalid KB ID**
   - If the destination KB ID was incorrect, the verification step will now catch this BEFORE attempting to remove the file from the source
   - Previously, this could have caused issues

3. **Heavy Load During File Listing**
   - The `list-files` operation that returned a 502 suggests the instance was under stress
   - Large KBs with many files can be resource-intensive

4. **API Rate Limiting**
   - Multiple rapid API calls might have triggered rate limiting or overwhelmed the backend

### Diagnostic Steps

1. **Check OpenWebUI Instance Status**
   ```bash
   # Check if your instance is accessible
   curl -H "Authorization: Bearer YOUR_API_KEY" https://your-instance.com/api/v1/knowledge/list
   ```

2. **Verify KB IDs**
   ```bash
   # List all KBs to get correct IDs
   kb-manager list-kbs --json
   ```

3. **Test with Small Operations First**
   ```bash
   # Try listing files in a KB (don't use the one that caused issues)
   kb-manager list-files <known-good-kb-id>
   ```

4. **Use Debug Logging**
   ```bash
   # Enable debug mode to see detailed API calls
   kb-manager --debug move-file <file-id> <dest-kb-id> --from-kb <source-kb-id>
   ```

5. **Check Backend Logs**
   - Review your OpenWebUI/Render logs for error messages
   - Look for out-of-memory errors, database connection issues, or Python tracebacks
   - Check if there are any ERROR or CRITICAL level log messages

## Recommended Approach Going Forward

### 1. Validate Before Moving
```bash
# Step 1: List available KBs and verify IDs
kb-manager list-kbs

# Step 2: Verify source KB exists and contains the file
kb-manager list-files <source-kb-id> | grep <file-id>

# Step 3: Verify destination KB exists (will also verify it's accessible)
kb-manager list-files <dest-kb-id>

# Step 4: Now move with confidence
kb-manager move-file <file-id> <dest-kb-id> --from-kb <source-kb-id>
```

### 2. Monitor Instance Health
- Keep an eye on your Render metrics during operations
- If the instance shows high memory or CPU usage, wait before running more commands
- Consider scaling up your instance if you're working with large KBs

### 3. Use Smaller Batches
- If you need to move many files, do them one at a time with pauses between
- Don't run multiple move operations in parallel

## API Endpoints Used

The move-file command uses these OpenWebUI API endpoints:

1. **Verify KB**: `GET /api/v1/knowledge/{kb_id}` (via list_files)
2. **Remove from KB**: `POST /api/v1/knowledge/{kb_id}/file/remove`
   - Body: `{"file_id": "..."}`
3. **Add to KB**: `POST /api/v1/knowledge/{kb_id}/file/add`
   - Body: `{"file_id": "..."}`

Note: These are POST endpoints (not DELETE), which is what the OpenWebUI API expects based on the generated client.

## If You Encounter Issues

### If the instance crashes again:
1. **Wait for the instance to recover** - Render should automatically restart it
2. **Check if the file was orphaned**:
   ```bash
   # Try to find the file in both KBs
   kb-manager list-files <source-kb-id> | grep <file-id>
   kb-manager list-files <dest-kb-id> | grep <file-id>
   ```
3. **If orphaned, re-add it**:
   ```bash
   # Add it to the intended destination (no --from-kb)
   kb-manager move-file <file-id> <dest-kb-id>
   ```

### If verification is causing issues:
```bash
# Use skip-verify as a last resort
kb-manager move-file <file-id> <dest-kb-id> --from-kb <source-kb-id> --skip-verify
```

### Get help:
- Include the full error message
- Include debug logs (`--debug` flag)
- Include the OpenWebUI backend logs from Render
- Note the KB sizes (number of files) involved

## Technical Notes

### Why Pre-flight Checks?
Pre-flight verification prevents the worst-case scenario: removing a file from the source KB but then being unable to add it to the destination KB (because it doesn't exist or is inaccessible). By checking first, we ensure the operation can complete successfully.

### Why the Crash Might Not Be Related
The kb-manager tool is just an API client - it sends HTTP requests to your OpenWebUI instance. It cannot directly crash the backend service. However, it's possible that:
- The API requests triggered a bug in the OpenWebUI backend
- The backend was already under stress and these requests were the "straw that broke the camel's back"
- There's a resource leak or infinite loop in the backend's file handling code

### Reporting Backend Issues
If you consistently can reproduce a crash with specific operations, this should be reported to the OpenWebUI project as a potential backend bug. Include:
- OpenWebUI version
- Steps to reproduce
- Backend logs showing the crash
- Memory/CPU metrics at the time of crash

