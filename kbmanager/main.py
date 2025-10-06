# kbmanager/main.py

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

import click

from kbmanager.api_interface import KBManagerAPIInterface  # This should be the only API-related import
from kbmanager.app_logic import AppLogic
from kbmanager.config_manager import ConfigManager
from kbmanager.exceptions import APIError, ConfigError, FileOperationError

from kbmanager.utils import get_actual_client_instance

logger = logging.getLogger(__name__)

class CLIContext:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.api_client_raw: Optional[Any] = None  # The direct generated client from api_client.client
        self.api_interface: Optional[KBManagerAPIInterface] = None  # The wrapper interface
        self.app_logic: Optional[AppLogic] = None
        self.config = {}

    def init_api_client_and_app_logic(self):
        # Only initialize if app_logic is not already set
        if self.app_logic is None:
            try:
                # 1. Get the raw AuthenticatedClient instance
                self.api_client_raw = get_actual_client_instance(self.config_manager)

                # 2. Pass the raw client to KBManagerAPIInterface
                self.api_interface = KBManagerAPIInterface(self.api_client_raw)

                # 3. Pass the APIInterface to AppLogic
                self.app_logic = AppLogic(self.api_interface)
            except (ConfigError, RuntimeError) as e:
                logger.error(f"Error during API client initialization: {e}")
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)


def coro(f):
    import functools

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", stream=sys.stderr
)


# Single CLI definition
@click.group(context_settings={"obj": CLIContext()}, invoke_without_command=True)
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@click.option("--api-key", envvar="KB_MANAGER_API_KEY", help="OpenWebUI API Key.")
@click.option("--api-url", envvar="KB_MANAGER_BASE_URL", help="OpenWebUI API Base URL (e.g., http://localhost:8080).")
@click.pass_context
def cli(ctx, debug, api_key, api_url):
    """
    KB-Manager CLI for managing files and knowledge bases in OpenWebUI.
    """
    if ctx.invoked_subcommand is None:
        click.echo("KB-Manager CLI for OpenWebUI.")
        click.echo(ctx.get_help())
        sys.exit(0)

    # Load configuration
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled.")

    cli_args = {"api_key": api_key, "base_url": api_url}
    cli_args = {k: v for k, v in cli_args.items() if v is not None}

    try:
        ctx.obj.config = ctx.obj.config_manager.load_config(cli_args)
        logger.debug("Configuration loaded successfully.")
    except ConfigError as e:
        if ctx.invoked_subcommand == "setup":
            logger.info(f"Config error during early setup of context (expected if no config yet): {e}")
        else:
            logger.error(f"Configuration error: {e}")
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.argument("name")
@click.option("--description", help="Description for the new knowledge base.")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
@click.pass_obj
@coro
async def create_kb(ctx: CLIContext, name, description, json_output):
    """
    Creates a new knowledge base.
    """
    ctx.init_api_client_and_app_logic()
    logger.info(f"Creating Knowledge Base: {name}")
    try:
        kb_info = await ctx.app_logic.create_knowledge_base(name, description)

        if json_output:
            kb_dict = {"id": kb_info.id, "name": kb_info.name, "description": kb_info.description}
            click.echo(json.dumps(kb_dict, indent=2))
        else:
            click.echo("Successfully created Knowledge Base:")
            click.echo(f"  Name: {kb_info.name}")
            click.echo(f"  ID:   {kb_info.id}")
            if kb_info.description:
                click.echo(f"  Desc: {kb_info.description}")
    except APIError as e:
        logger.error(f"Failed to create Knowledge Base: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
@click.pass_obj
@coro
async def list_kbs(ctx: CLIContext, json_output):
    """
    Lists all available knowledge bases.
    """
    ctx.init_api_client_and_app_logic()
    try:
        kbs = await ctx.app_logic.list_knowledge_bases()

        if json_output:
            kbs_list_dicts = [{"id": kb.id, "name": kb.name, "description": kb.description} for kb in kbs]
            click.echo(json.dumps(kbs_list_dicts, indent=2))
        else:
            if not kbs:
                click.echo("No knowledge bases found.")
                return

            click.echo("Found Knowledge Bases:")
            for kb in kbs:
                click.echo(f"  - Name: {kb.name}")
                click.echo(f"    ID:   {kb.id}")
                if kb.description:
                    click.echo(f"  Desc: {kb.description}")
                click.echo("-" * 20)
    except APIError as e:
        logger.error(f"Failed to list Knowledge Bases: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--kb-id", required=True, help="ID of the knowledge base to add the file to.")
@click.pass_obj
@coro
async def upload_file(ctx: CLIContext, file_path, kb_id):
    """
    Uploads a single file to a specified knowledge base.
    """
    ctx.init_api_client_and_app_logic()
    click.echo(f"Uploading file: {file_path}")
    try:
        await ctx.app_logic.upload_file_to_kb(file_path, kb_id)
    except (APIError, FileOperationError) as e:
        logger.error(f"Could not complete file upload: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("directory_path", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option("--kb-id", required=True, help="ID of the knowledge base to add the files to.")
@click.option(
    "--ignore-file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to a .kbignore file. Defaults to .kbignore in the directory_path if not specified.",
)
@click.pass_obj
@coro
async def upload_dir(ctx: CLIContext, directory_path, kb_id, ignore_file):
    """
    Uploads files from a directory to a specified knowledge base, respecting .kbignore.
    """
    ctx.init_api_client_and_app_logic()
    click.echo(f"Uploading directory: {directory_path}")
    try:
        await ctx.app_logic.upload_directory_to_kb(directory_path, kb_id, ignore_file)
    except (APIError, FileOperationError) as e:
        logger.error(f"Could not complete directory upload: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("file_id")
@click.argument("new_file_path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.pass_obj
@coro
async def update_file(ctx: CLIContext, file_id, new_file_path):
    """
    Updates the content of an existing file by its OpenWebUI ID.
    """
    ctx.init_api_client_and_app_logic()
    click.echo(f"Updating file ID: {file_id}")
    try:
        await ctx.app_logic.update_file_content(file_id, new_file_path)
    except (APIError, FileOperationError) as e:
        logger.error(f"Could not update file content: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("file_id")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
@click.pass_obj
@coro
async def get_file(ctx: CLIContext, file_id, json_output):
    """
    Gets details about a specific file by its ID (useful for checking if a file exists).
    """
    ctx.init_api_client_and_app_logic()
    try:
        file_info = await ctx.api_interface.get_file_by_id(file_id)
        if json_output:
            import json
            # Convert to dict - file_info might be a model object
            if hasattr(file_info, 'to_dict'):
                file_dict = file_info.to_dict()
            else:
                file_dict = {"info": str(file_info)}
            click.echo(json.dumps(file_dict, indent=2))
        else:
            click.echo(f"File found: {file_id}")
            if hasattr(file_info, 'filename'):
                click.echo(f"  Filename: {file_info.filename}")
            if hasattr(file_info, 'user_id'):
                click.echo(f"  User ID: {file_info.user_id}")
            click.echo(f"  Full info: {file_info}")
    except APIError as e:
        logger.error(f"Could not get file: {e}")
        click.echo(f"Error: File not found or inaccessible: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument("file_id")
@click.pass_obj
@coro
async def delete_file(ctx: CLIContext, file_id):
    """
    Deletes a file by its OpenWebUI ID.
    """
    ctx.init_api_client_and_app_logic()
    click.echo(f"Deleting file ID: {file_id}")
    try:
        await ctx.app_logic.delete_file(file_id)
    except APIError as e:
        logger.error(f"Could not delete file: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument("file_id")
@click.argument("destination_kb_id")
@click.option("--from-kb", "source_kb_id", help="Source knowledge base ID (for reference only - file will be COPIED, not moved).")
@click.option("--skip-verify", is_flag=True, help="Skip pre-flight KB verification checks (not recommended).")
@click.pass_obj
@coro
async def move_file(ctx: CLIContext, file_id, destination_kb_id, source_kb_id, skip_verify):
    """
    ⚠️  CRITICAL UPDATE: This command now COPIES files instead of moving them!
    
    Due to OpenWebUI API limitations (removing a file from a KB deletes it entirely),
    this command has been changed to COPY files to the destination KB while leaving
    them in the source KB.
    
    FILE_ID is the ID of the file to copy.
    DESTINATION_KB_ID is the target knowledge base ID.
    
    The file will exist in BOTH the source and destination KBs after this operation.
    
    ⚠️  WARNING: Do NOT manually remove files from a KB unless you're certain they
    exist in other KBs, as removal DELETES the file entirely from the system!
    
    Use --from-kb to specify the source KB for reference purposes.
    Safety checks are performed by default to verify KBs exist.
    """
    ctx.init_api_client_and_app_logic()
    
    if skip_verify:
        click.echo(click.style("⚠️  Warning: Skipping pre-flight verification checks", fg='yellow'))
    
    if source_kb_id:
        click.echo(f"Copying file '{file_id}' from KB '{source_kb_id}' to KB '{destination_kb_id}'...")
    else:
        click.echo(f"Adding file '{file_id}' to KB '{destination_kb_id}'...")
    
    try:
        await ctx.app_logic.move_file_between_kbs(file_id, source_kb_id, destination_kb_id, skip_verify=skip_verify)
    except (APIError, FileOperationError) as e:
        logger.error(f"Could not copy file: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('kb_id')
@click.option('--yes', is_flag=True, help='Skip confirmation prompt.')
@click.pass_obj
@coro
async def delete_all_files(ctx: CLIContext, kb_id: str, yes: bool):
    """
    Deletes ALL files belonging to a specified knowledge base.
    This action is irreversible.
    """
    ctx.init_api_client_and_app_logic()
    logger.info(f"Attempting to delete all files from Knowledge Base ID: {kb_id}")

    if not yes:
        click.echo(click.style(f"WARNING: This will delete ALL files from Knowledge Base '{kb_id}'. This action is irreversible!", fg='red', bold=True))
        if not click.confirm("Are you sure you want to proceed?"):
            click.echo("Operation cancelled.")
            return

    try:
        await ctx.app_logic.delete_all_files_from_kb(kb_id)
        click.echo(click.style(f"✅ Successfully initiated deletion of all files from Knowledge Base '{kb_id}'.", fg='green'))
    except APIError as e:
        logger.error(f"Could not delete all files from KB '{kb_id}': {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting all files from KB '{kb_id}': {e}", exc_info=True)
        click.echo(f"An unexpected error occurred: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument("kb_id")
@click.option("--search", help="Search query to filter files by (e.g., filename, path).")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
@click.pass_obj
@coro
async def list_files(ctx: CLIContext, kb_id, search, json_output):
    """
    Lists files for a specific knowledge base.
    """
    ctx.init_api_client_and_app_logic()
    logger.info(f"Listing files for KB '{kb_id}'...")
    try:
        files = await ctx.app_logic.list_files(kb_id, search)

        if json_output:
            files_list_dicts = []
            for f in files:
                additional_meta = (
                    f.meta.additional_properties
                    if hasattr(f, "meta") and hasattr(f.meta, "additional_properties")
                    else {}
                )

                file_dict = {
                    "id": f.id,
                    "filename": additional_meta.get("name", "[Filename Missing]"),
                    "filepath": additional_meta.get("collection_name", "[Filepath Missing]"),
                    "mime_type": additional_meta.get("content_type", "[MIME Type Missing]"),
                    "size": additional_meta.get("size", 0),
                    "meta_raw": additional_meta,
                }
                files_list_dicts.append(file_dict)
            click.echo(json.dumps(files_list_dicts, indent=2))
        else:
            if not files:
                click.echo(f"No files found for Knowledge Base '{kb_id}'" + (f" matching '{search}'" if search else ""))
                return

            click.echo(f"Found {len(files)} Files for KB '{kb_id}':")
            for f in files:
                additional_meta = (
                    f.meta.additional_properties
                    if hasattr(f, "meta") and hasattr(f.meta, "additional_properties")
                    else {}
                )

                filename = additional_meta.get("name", "[Filename Missing]")
                filepath = additional_meta.get("collection_name", "[Filepath Missing]")

                click.echo(f"  - Filename: {filename}")
                click.echo(f"    ID:       {f.id}")
                click.echo(f"    Path:     {filepath}")
                click.echo("-" * 20)
    except APIError as e:
        logger.error(f"Could not list files: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
