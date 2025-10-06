# kbmanager/utils.py
import logging
import sys

logger = logging.getLogger(__name__)


def get_authenticated_client_class():
    """Dynamically imports and returns AuthenticatedClient."""
    try:
        from kbmanager.open_web_ui_client.client import AuthenticatedClient

        return AuthenticatedClient
    except ModuleNotFoundError as e:
        logger.error(f"Error importing API client: {e}. The 'open_web_ui_client' module might be missing.")
        click.echo("Error: The 'open_web_ui_client' module is missing. It needs to be generated.")
        click.echo("Please run 'kb-manager setup' to generate the API client.")
        sys.exit(1)  # Exit if client not found


def get_actual_client_instance(config_manager):
    """
    Returns an instance of AuthenticatedClient using configuration.
    Raises ConfigError or RuntimeError if configuration is missing or client cannot be initialized.
    """
    AuthenticatedClient = get_authenticated_client_class()
    try:
        # Ensure config_manager has loaded config before accessing properties
        if not config_manager.get("api_key") or not config_manager.get("base_url"):
            raise ConfigError(
                "API key or base URL is missing. Please ensure configuration is loaded or run 'kb-manager setup'."
            )

        return AuthenticatedClient(
            base_url=config_manager.base_url, token=config_manager.api_key, follow_redirects=True
        )
    except ConfigError as e:
        logger.error(f"Configuration error during client initialization: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during API client instantiation: {e}")
        raise RuntimeError(f"Failed to initialize API client: {e}")
