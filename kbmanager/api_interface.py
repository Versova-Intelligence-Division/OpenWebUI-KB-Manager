# kbmanager/api_interface.py

import json
import logging
import mimetypes
from pathlib import Path
from typing import Any, List, Optional

from tqdm import tqdm

from kbmanager.exceptions import APIError, FileOperationError

# THESE IMPORTS ARE OKAY *ONLY HERE* (because this file is not imported by main.py
# until the client is guaranteed to exist).
try:
    from kbmanager.open_web_ui_client.api.files.delete_file_by_id_api_v1_files_id_delete import (
        asyncio_detailed as delete_file_async_detailed,
    )
    from kbmanager.open_web_ui_client.api.files.update_file_data_content_by_id_api_v1_files_id_data_content_update_post import (
        asyncio_detailed as update_file_content_async_detailed,
    )
    from kbmanager.open_web_ui_client.api.files.upload_file_api_v1_files_post import (
        asyncio_detailed as upload_file_async_detailed,
    )
    from kbmanager.open_web_ui_client.api.knowledge.add_files_to_knowledge_batch_api_v1_knowledge_id_files_batch_add_post import (
        asyncio_detailed as add_files_to_kb_batch_async_detailed,
    )

    # API operation functions
    from kbmanager.open_web_ui_client.api.knowledge.create_new_knowledge_api_v1_knowledge_create_post import (
        asyncio_detailed as create_kb_async_detailed,
    )
    from kbmanager.open_web_ui_client.api.knowledge.get_knowledge_by_id_api_v1_knowledge_id_get import (
        asyncio_detailed as get_files_by_kb_id_async_detailed,
    )
    from kbmanager.open_web_ui_client.api.knowledge.get_knowledge_list_api_v1_knowledge_list_get import (
        asyncio_detailed as list_kbs_async_detailed,
    )
    from kbmanager.open_web_ui_client.client import AuthenticatedClient
    from kbmanager.open_web_ui_client.models import (
        BodyUploadFileApiV1FilesPost,
        ContentForm,
        FileMetadataResponse,
        FileModelResponse,
        KnowledgeFileIdForm,
        KnowledgeFilesResponse,
        KnowledgeForm,
    )
    from kbmanager.open_web_ui_client.models.file_metadata_response_meta import FileMetadataResponseMeta
    from kbmanager.open_web_ui_client.types import File as OpenAPIGeneratedFile

    _client_imported_successfully = True
except ModuleNotFoundError as e:
    _client_imported_successfully = False
    _import_error_message = str(e)
    # Log this for debugging but don't re-raise yet, provide a placeholder class
    logging.getLogger(__name__).debug(f"API client not found during api_interface import: {_import_error_message}")

logger = logging.getLogger(__name__)

# Placeholder classes for when the client isn't imported
if not _client_imported_successfully:

    class AuthenticatedClient:
        pass

    class FileModelResponse:
        pass

    class KnowledgeForm:
        pass

    class BodyUploadFileApiV1FilesPost:
        pass

    class KnowledgeFileIdForm:
        pass

    class KnowledgeFilesResponse:
        pass

    class FileMetadataResponse:
        pass

    class OpenAPIGeneratedFile:
        pass

    class FileMetadataResponseMeta:
        pass  # Add this if used

    def _uninitialized_method(*args, **kwargs):
        raise RuntimeError(
            f"API client is not initialized. Please run `kb-manager setup`.\n(Original error: {_import_error_message})"
        )

    # Use _uninitialized_method as placeholders for all api call functions if client not imported.
    create_kb_async_detailed = _uninitialized_method
    list_kbs_async_detailed = _uninitialized_method
    add_files_to_kb_batch_async_detailed = _uninitialized_method
    get_files_by_kb_id_async_detailed = _uninitialized_method
    upload_file_async_detailed = _uninitialized_method
    delete_file_async_detailed = _uninitialized_method
    update_file_content_async_detailed = _uninitialized_method


class KBManagerAPIInterface:
    """
    Acts as an interface to the OpenAPI generated client.
    This class handles the direct interaction with generated client functions and models.
    It will only be instantiated if the API client is present.
    """

    def __init__(self, open_web_ui_client: AuthenticatedClient):
        if not _client_imported_successfully:
            raise RuntimeError(
                "Cannot initialize KBManagerAPIInterface: API client modules not found.\nPlease run `kb-manager setup`."
            )
        self._client = open_web_ui_client

    def _get_file_content(self, file_path: Path) -> bytes:
        # Re-include this helper from AppLogic if it's only for file reading
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except OSError as e:
            raise FileOperationError(f"Error reading file {file_path}: {e}")

    async def upload_single_file_with_progress(self, file_path: Path) -> FileModelResponse:
        file_size = file_path.stat().st_size
        file_name = file_path.name

        file_content_bytes = self._get_file_content(file_path)

        mime_type, _ = mimetypes.guess_type(file_name)
        if mime_type is None:
            mime_type = "application/octet-stream"

        generated_file_object = OpenAPIGeneratedFile(
            file_name=file_name, payload=file_content_bytes, mime_type=mime_type
        )

        file_upload_request_body = BodyUploadFileApiV1FilesPost(
            file=generated_file_object,
        )

        response = await upload_file_async_detailed(
            client=self._client,
            body=file_upload_request_body,
            process=True,
            internal=False,
        )

        if response.status_code != 200 or not response.parsed:
            error_message = response.content.decode("utf-8", errors="ignore")
            if response.status_code == 422:
                try:
                    error_details = json.loads(error_message)
                    detail_str = ""
                    if isinstance(error_details, dict) and "detail" in error_details:
                        details = error_details["detail"]
                        if isinstance(details, list):
                            detail_str = "; ".join([f"{d.get('loc', [])}: {d.get('msg')}" for d in details])
                        else:
                            detail_str = str(details)
                    error_message = f"Validation Error (422): {detail_str or error_message}"
                except json.JSONDecodeError:
                    pass
            raise APIError(
                f"File upload failed with status {response.status_code}: {error_message}",
                status_code=response.status_code,
                response_content=error_message,
            )

        uploaded_file = response.parsed


        logger.info(f"Successfully uploaded {file_path.name} as ID: {uploaded_file.id}")
        return uploaded_file

    async def create_knowledge_base(
        self, name: str, description: Optional[str] = None
    ) -> KnowledgeForm:  # Return type depends on what API returns
        kb_form = KnowledgeForm(name=name, description=description)
        response = await create_kb_async_detailed(body=kb_form, client=self._client)

        if response.status_code != 200 or not response.parsed:
            error_message = response.content.decode("utf-8", errors="ignore")
            raise APIError(
                f"Failed to create KB: {error_message}",
                status_code=response.status_code,
                response_content=error_message,
            )
        return response.parsed

    async def list_knowledge_bases(self) -> List[Any]:  # What the API returns
        response = await list_kbs_async_detailed(client=self._client)
        if response.status_code != 200:
            error_message = response.content.decode("utf-8", errors="ignore")
            raise APIError(
                f"Failed to list KBs (HTTP {response.status_code}): {error_message}",
                status_code=response.status_code,
                response_content=error_message,
            )
        return json.loads(response.content.decode("utf-8", errors="ignore"))

    async def add_files_to_knowledge_base_batch(self, kb_id: str, file_ids: List[str]):
        forms = [KnowledgeFileIdForm(file_id=fid) for fid in file_ids]
        response = await add_files_to_kb_batch_async_detailed(id=kb_id, body=forms, client=self._client)
        if response.status_code != 200:
            error_message = response.content.decode("utf-8", errors="ignore")
            raise APIError(
                f"Failed to link files to KB: {error_message}",
                status_code=response.status_code,
                response_content=error_message,
            )
        return True  # Or some useful response status

    async def delete_file_by_id(self, file_id: str):
        response = await delete_file_async_detailed(id=file_id, client=self._client)
        if response.status_code != 200:
            error_message = response.content.decode("utf-8", errors="ignore")
            raise APIError(
                f"File deletion failed: {error_message}",
                status_code=response.status_code,
                response_content=error_message,
            )
        return True

    async def update_file_content_by_id(self, file_id: str, new_file_path: Path):
        content_bytes = self._get_file_content(new_file_path)
        # Decode bytes to string - try UTF-8 first, fall back to latin-1 if needed
        try:
            content_str = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            content_str = content_bytes.decode('latin-1')
        
        # Create ContentForm object as expected by the API
        content_form = ContentForm(content=content_str)
        
        with tqdm(
            total=len(content_bytes),
            unit="B",
            unit_scale=True,
            desc=f"Updating {file_id}",
            ncols=100,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} {rate_fmt}",
            leave=False,
        ) as pbar:
            response = await update_file_content_async_detailed(id=file_id, body=content_form, client=self._client)
            if response.status_code != 200 or not response.parsed:
                error_message = response.content.decode("utf-8", errors="ignore")
                if response.status_code == 422:
                    try:
                        error_details = json.loads(error_message)
                        detail_str = ""
                        if isinstance(error_details, dict) and "detail" in error_details:
                            details = error_details["detail"]
                            if isinstance(details, list):
                                detail_str = "; ".join([f"{d.get('loc', [])}: {d.get('msg')}" for d in details])
                            else:
                                detail_str = str(details)
                        error_message = f"Validation Error (422): {detail_str or error_message}"
                    except json.JSONDecodeError:
                        pass
                raise APIError(
                    f"Content update failed with status {response.status_code}: {error_message}",
                    status_code=response.status_code,
                    response_content=error_message,
                )
            updated_file = response.parsed
            pbar.update(len(content_bytes))
        return updated_file

    async def list_files_for_knowledge_base(self, kb_id: str) -> List[FileMetadataResponse]:
        response = await get_files_by_kb_id_async_detailed(id=kb_id, client=self._client)
        if response.status_code != 200:
            error_message = response.content.decode("utf-8", errors="ignore")
            raise APIError(
                f"Failed to retrieve KB {kb_id} details: {error_message}",
                status_code=response.status_code,
                response_content=error_message,
            )

        parsed_response = response.parsed
        if hasattr(parsed_response, "files") and isinstance(parsed_response.files, list):
            return parsed_response.files
        # Fallback for old API versions or variations
        elif (
            hasattr(parsed_response, "data")
            and isinstance(parsed_response.data, dict)
            and "files" in parsed_response.data
            and isinstance(parsed_response.data["files"], list)
        ):
            return parsed_response.data["files"]
        return []

    # Expose the API client's internal types if AppLogic needs them (e.g. for return types)
    @property
    def FileMetadataResponse(self):
        return FileMetadataResponse

    @property
    def FileMetadataResponseMeta(self):
        return FileMetadataResponseMeta

    @property
    def KnowledgeFileIdForm(self):
        return KnowledgeFileIdForm

    @property
    def FileModelResponse(self):
        return FileModelResponse
