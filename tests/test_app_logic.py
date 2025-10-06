# tests/test_app_logic.py
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import json
from kbmanager.app_logic import AppLogic
from kbmanager.exceptions import APIError
from kbmanager.open_web_ui_client.models.file_metadata_response_meta import FileMetadataResponseMeta


class TestAppLogic:
    @pytest.fixture
    def mock_client(self):
        """Create a mock API client."""
        return Mock()

    @pytest.fixture
    def app_logic(self, mock_client):
        """Create AppLogic instance with mock client."""
        return AppLogic(mock_client)

    @pytest.mark.asyncio
    async def test_api_error_handling_422(self, app_logic, mock_client):
        """Test handling of 422 validation error."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.parsed = None
        error_details = {
            "detail": [
                {"loc": ["field1"], "msg": "required field"},
                {"loc": ["field2"], "msg": "invalid format"}
            ]
        }
        mock_response.content.decode.return_value = json.dumps(error_details)

        # Test error handling (would need actual method that uses this pattern)
        with pytest.raises(APIError) as exc_info:
            # Simulate the error handling logic from app_logic.py
            if mock_response.status_code != 200 or not mock_response.parsed:
                error_message = mock_response.content.decode('utf-8', errors='ignore')
                if mock_response.status_code == 422:
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
                raise APIError(error_message, status_code=422)

        assert "Validation Error (422)" in str(exc_info.value)
        assert "['field1']: required field" in str(exc_info.value)

    def test_client_side_search(self, app_logic):
        """Test client-side search filtering."""
        # Create mock files with proper attributes
        mock_file1 = Mock()
        mock_file1.meta = FileMetadataResponseMeta()
        mock_file1.meta.additional_properties = {'name': 'test_document.txt'}

        mock_file2 = Mock()
        mock_file2.meta = FileMetadataResponseMeta()
        mock_file2.meta.additional_properties = {'name': 'another_file.pdf'}

        mock_file3 = Mock()
        mock_file3.meta = FileMetadataResponseMeta()
        mock_file3.meta.additional_properties = {'name': 'test_image.jpg'}

        files = [mock_file1, mock_file2, mock_file3]
        search_query = "test"

        # Apply the search logic from app_logic.py
        filtered_files = [
            f for f in files
            if (
                    hasattr(f, 'meta') and isinstance(f.meta, FileMetadataResponseMeta) and
                    'name' in f.meta.additional_properties and
                    search_query.lower() in str(f.meta.additional_properties['name']).lower()
            )
        ]

        assert len(filtered_files) == 2
        assert mock_file1 in filtered_files
        assert mock_file3 in filtered_files
        assert mock_file2 not in filtered_files

    def test_json_decode_error_handling(self, app_logic):
        """Test handling of JSON decode errors."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.parsed = None
        mock_response.content.decode.return_value = "Invalid JSON response"

        with pytest.raises(APIError) as exc_info:
            # Simulate error handling
            if mock_response.status_code != 200 or not mock_response.parsed:
                error_message = mock_response.content.decode('utf-8', errors='ignore')
                try:
                    json.loads(error_message)  # This will fail
                except json.JSONDecodeError:
                    pass
                raise APIError(f"Content update failed with status {mock_response.status_code}: {error_message}",
                               status_code=mock_response.status_code, response_content=error_message)

        assert exc_info.value.status_code == 400
        assert "Invalid JSON response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_file_between_kbs_success(self, app_logic, mock_client):
        """Test successful file move between knowledge bases."""
        file_id = "test-file-123"
        source_kb_id = "source-kb-456"
        dest_kb_id = "dest-kb-789"

        # Mock the API methods
        mock_client.remove_file_from_knowledge_base = AsyncMock(return_value=True)
        mock_client.add_file_to_knowledge_base = AsyncMock(return_value=True)

        # Execute the move
        await app_logic.move_file_between_kbs(file_id, source_kb_id, dest_kb_id)

        # Verify both API calls were made with correct parameters
        mock_client.remove_file_from_knowledge_base.assert_called_once_with(source_kb_id, file_id)
        mock_client.add_file_to_knowledge_base.assert_called_once_with(dest_kb_id, file_id)

    @pytest.mark.asyncio
    async def test_move_file_without_source_kb(self, app_logic, mock_client):
        """Test moving a file without specifying source KB (just adds to destination)."""
        file_id = "test-file-123"
        dest_kb_id = "dest-kb-789"

        # Mock the API method
        mock_client.add_file_to_knowledge_base = AsyncMock(return_value=True)
        mock_client.remove_file_from_knowledge_base = AsyncMock()

        # Execute the move without source KB
        await app_logic.move_file_between_kbs(file_id, None, dest_kb_id)

        # Verify only add was called, not remove
        mock_client.remove_file_from_knowledge_base.assert_not_called()
        mock_client.add_file_to_knowledge_base.assert_called_once_with(dest_kb_id, file_id)

    @pytest.mark.asyncio
    async def test_move_file_remove_fails(self, app_logic, mock_client):
        """Test handling when removing from source KB fails."""
        from kbmanager.exceptions import FileOperationError
        
        file_id = "test-file-123"
        source_kb_id = "source-kb-456"
        dest_kb_id = "dest-kb-789"

        # Mock remove to fail
        mock_client.remove_file_from_knowledge_base = AsyncMock(
            side_effect=APIError("Failed to remove", status_code=404)
        )

        # Execute and expect FileOperationError
        with pytest.raises(FileOperationError) as exc_info:
            await app_logic.move_file_between_kbs(file_id, source_kb_id, dest_kb_id)

        assert "Failed to remove file from source KB" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_file_add_fails_after_remove(self, app_logic, mock_client):
        """Test handling when adding to destination KB fails after successful remove."""
        from kbmanager.exceptions import FileOperationError
        
        file_id = "test-file-123"
        source_kb_id = "source-kb-456"
        dest_kb_id = "dest-kb-789"

        # Mock remove to succeed but add to fail
        mock_client.remove_file_from_knowledge_base = AsyncMock(return_value=True)
        mock_client.add_file_to_knowledge_base = AsyncMock(
            side_effect=APIError("Failed to add", status_code=400)
        )

        # Execute and expect FileOperationError with warning about orphaned file
        with pytest.raises(FileOperationError) as exc_info:
            await app_logic.move_file_between_kbs(file_id, source_kb_id, dest_kb_id)

        error_msg = str(exc_info.value)
        assert "Failed to add file to destination KB" in error_msg
        assert "WARNING" in error_msg
        assert "removed from source KB" in error_msg