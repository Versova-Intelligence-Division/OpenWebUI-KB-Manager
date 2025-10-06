# KB-Manager Bug Report and Workarounds

This document tracks known bugs and their temporary workarounds.

## `create-kb` Command Fails Without a Description

**Issue:**

When using the `create-kb` command and providing only a name, the command fails with a `422 Unprocessable Entity` error. The OpenWebUI API expects a string for the `description` field, but the tool sends a `null` value when the `--description` option is omitted, causing a validation error.

**Error Message:**

```
Error: Failed to create KB: {"detail":[{"type":"string_type","loc":["body","description"],"msg":"Input should be a valid string","input":null}]}
```

**Workaround:**

To successfully create a knowledge base, you must explicitly provide an empty string for the description using the `--description` flag.

**Correct Syntax:**

```bash
kb-manager create-kb "Your Knowledge Base Name" --description ""
```

---

## `update-file` Command Fails with 422 Error

**Issue:**

The `update-file` command is fundamentally broken. The generated API client is designed to send JSON payloads, but the `/api/v1/files/{id}/data/content/update` endpoint expects raw binary data (`application/octet-stream`). Attempts to force the client to send the correct data type and `Content-Type` header have failed, consistently resulting in a `422 Unprocessable Entity` error from the server.

**Error Message:**

```
Error updating file content: Content update failed with status 422: Validation Error (422): ['body']: Input should be a valid dictionary or object to extract fields from
```

**Workaround:**

There is currently no workaround for this issue. The command cannot be used until the underlying API client generation is fixed to correctly handle binary file uploads for this specific endpoint.

---

*Further issues will be documented here as they are discovered.*
