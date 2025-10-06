# KB-Manager

A command-line interface (CLI) tool for managing files and knowledge bases in OpenWebUI.

## Features

-   **Knowledge Base Management**: Create new knowledge bases and list existing ones.
-   **File Operations**: Upload, update, delete, and list files.
-   **Batch Directory Uploads**: Upload entire directories, with support for ignore patterns via `.kbignore` files.
-   **Flexible Configuration**: Configure via a local `config.yaml`, environment variables, or CLI arguments.
-   **JSON Output**: Optional JSON output for programmatic use and scripting.

## Installation

### Prerequisites

-   Python 3.11 or higher.
-   An active OpenWebUI instance.

### Install from Source 

```bash
git clone https://github.com/dubh3124/kb-manager.git
cd kb-manager
pip install -e .
```

## Getting Started

Because this tool no longer generates its own client, getting started is as simple as providing your API credentials. KB-Manager can be configured through multiple methods, which are loaded in the following order of precedence:

1.  **CLI Arguments** (`--api-key`, `--api-url`)
2.  **Environment Variables**
3.  **Configuration File**

### Step 1: Obtain Your API Key

Log in to your OpenWebUI instance, navigate to **Settings -> Account -> API Keys**, and create a new key.

### Step 2: Configure the Tool

Choose **one** of the following methods to configure `kb-manager`.

#### Method A: Configuration File (Recommended for Regular Use)

Create a configuration file at `~/.kbmanager/config.yaml`.

```bash
# Create the directory
mkdir -p ~/.kbmanager

# Create and edit the config file
nano ~/.kbmanager/config.yaml
```

Add the following content to the file:

```yaml
# ~/.kbmanager/config.yaml
api_key: "your_api_key_here"
base_url: "http://your-open-webui-instance:8080"
```

*You can also place a `config.yaml` file in your current working directory.*

#### Method B: Environment Variables

Set the following environment variables in your terminal session:

```bash
export KB_MANAGER_API_KEY="your_api_key_here"
export KB_MANAGER_BASE_URL="http://your-open-webui-instance:8080"
```

### Step 3: Verify Your Setup

Run the `list-kbs` command to check your connection.

```bash
kb-manager list-kbs
```

If successful, you will see a list of your existing knowledge bases.

## Usage

### Global Options

-   `--debug`: Enable verbose debug logging.
-   `--api-key`: Override the API key from config/environment.
-   `--api-url`: Override the base URL from config/environment.

### Commands

| Command | Description | Example Usage |
| :--- | :--- | :--- |
| `list-kbs` | Lists all knowledge bases. | `kb-manager list-kbs` <br> `kb-manager list-kbs --json` |
| `create-kb <name>` | Creates a new knowledge base. | `kb-manager create-kb "My Research Notes"` |
| `upload-file <path>` | Uploads a single file to a KB. | `kb-manager upload-file doc.pdf --kb-id <id>` |
| `upload-dir <path>` | Uploads a directory to a KB. | `kb-manager upload-dir my-project --kb-id <id>` <br> `kb-manager upload-dir . --kb-id <id> --prefix-paths` |
| `update-file <file_id>` | Updates an existing file's content. | `kb-manager update-file <id> new-doc.pdf` |
| `get-file <file_id>` | Gets details about a file by its ID. | `kb-manager get-file <file-id>` <br> `kb-manager get-file <file-id> --json` |
| `delete-file <file_id>` | Deletes a file by its ID. | `kb-manager delete-file <id>` |
| `move-file <file_id> <dest_kb_id>` | **COPIES** a file to another KB (⚠️ see warning below). | `kb-manager move-file <file-id> <dest-kb-id> --from-kb <source-kb-id>` |
| `list-files <kb_id>` | Lists files in a specific KB. | `kb-manager list-files <id> --search "report"` |
| `delete-all-files <kb_id>`| Deletes ALL files from a specific KB. | `kb-manager delete-all-files <id> --yes` |

## Checking File Details

The `get-file` command allows you to retrieve information about a specific file by its ID. This is particularly useful for:

- **Verifying a file exists** before performing operations on it
- **Checking file metadata** like filename, user ID, and other properties
- **Troubleshooting** issues where files may have been accidentally deleted
- **Recovery operations** to confirm a file's status

### Usage

```bash
# Get basic file information
kb-manager get-file <file-id>

# Get detailed information in JSON format
kb-manager get-file <file-id> --json
```

### Example

```bash
# Check if a file exists
kb-manager get-file abc123

# Output:
# File found: abc123
#   Filename: document.pdf
#   User ID: user-456
#   Full info: <FileModel object details>

# Get JSON output for scripting
kb-manager get-file abc123 --json
```

### When to Use

- **Before moving/copying files**: Verify the file exists before attempting operations
- **After deletions**: Check if a file was actually deleted or just removed from a KB
- **Debugging**: When troubleshooting issues with file operations
- **Automation**: Use with `--json` flag in scripts to check file status

## ⚠️ CRITICAL: Moving/Copying Files Between Knowledge Bases

### 🔴 IMPORTANT WARNING

**The `move-file` command has been changed to COPY files instead of moving them!**

We discovered that OpenWebUI's API has a critical design issue: **removing a file from a KB DELETES the file entirely from the system**, not just removing the association. To prevent accidental data loss, this command now COPIES files to the destination while leaving them in the source.

### Usage

```bash
# Copy a file to another KB (file remains in both KBs)
kb-manager move-file <file-id> <destination-kb-id> --from-kb <source-kb-id>

# Add a file to an additional KB
kb-manager move-file <file-id> <destination-kb-id>
```

### ⚠️ What You Need to Know

1. **Files are COPIED, not moved**: After running this command, the file will exist in BOTH the source and destination KBs.

2. **DO NOT manually remove files**: OpenWebUI's "remove file from KB" operation DELETES the file permanently. Only remove files if you're absolutely certain they exist in multiple KBs.

3. **No true "move" operation exists**: Due to the API design, there's no safe way to move a file from one KB to another without risking data loss.

4. **Duplicate management**: If you want a file in only one KB, you'll need to manage duplicates yourself and be very careful about removal.

### How It Works Now

1. **Verification Phase** (unless `--skip-verify` is used):
   - Verifies destination KB exists and is accessible
   - If `--from-kb` is specified, verifies source KB exists
2. **Copy Phase**:
   - Adds the file to the destination knowledge base (creates a reference/copy)
   - **File remains in source KB** - it is NOT removed
3. **Result**: File exists in both KBs

### Safe Workflow Example

```bash
# 1. List all your KBs to get the correct IDs
kb-manager list-kbs

# 2. List files in the source KB to find the file you want to copy
kb-manager list-files <source-kb-id>

# 3. Copy the file to the destination KB
kb-manager move-file abc123 dest-kb-456 --from-kb source-kb-789

# 4. Verify the file is now in the destination KB
kb-manager list-files dest-kb-456

# 5. Verify the file still exists in the source KB
kb-manager list-files source-kb-789
```

### Recovery from Accidental Deletion

If you accidentally deleted a file (by removing it from its last KB), you'll need to:

1. **Re-upload the file**: Use `kb-manager upload-file <path> --kb-id <kb-id>`
2. **Check backups**: Look for the original file in your local backups
3. **Export from OpenWebUI**: If the file was backed up, export it from OpenWebUI's data directory

### Troubleshooting

1. **Verify KB IDs**: Use `kb-manager list-kbs` to ensure you have the correct KB IDs
2. **Check File ID**: Use `kb-manager list-files <kb-id>` to verify the file exists
3. **Verify File Exists**: Use `kb-manager get-file <file-id>` to check if a file exists in the system
4. **Use Debug Mode**: Run with `--debug` flag to see detailed API call information
5. **See Full Guide**: Refer to `TROUBLESHOOTING_MOVE_FILE.md` for detailed troubleshooting steps

## `.kbignore` Files

To exclude files during `upload-dir` operations, place a `.kbignore` file in the root of the directory you are uploading. The syntax is the same as `.gitignore`.

Example `.kbignore` content:

```gitignore
# Ignore all log files
*.log

# Ignore specific directories
__pycache__/
build/
.git/
.idea/

# Ignore this file itself
.kbignore
```

## Development and Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest
```

### Versioning and Releases

This project uses **[python-semantic-release](https://python-semantic-release.readthedocs.io/en/latest/)** to automate versioning and releases based on the **[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)** specification.

Releases are automatically triggered when commits are merged into the `main` branch.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built for seamless integration with [OpenWebUI](https://github.com/open-webui/open-webui).