"""
Integration tests for Airtable integration via IntegratedAPIService.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.services.integrated_api_service import IntegratedAPIService

# Mock base and table IDs for testing
BASE_ID = "apptest123"
TABLE_NAME = "Costs"
AIRTABLE_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

@pytest.mark.integration
class TestAirtableIntegration:
    """Test Airtable integration using the IntegratedAPIService with mocked API responses."""

    @pytest.fixture
    def mock_current_user(self):
        """Mock current user."""
        mock_user = MagicMock()
        mock_user.id = "user123"
        return mock_user

    @pytest.fixture
    def mock_api_key_resolver(self):
        """Mock API key resolver."""
        mock_resolver = MagicMock()
        resolved_key_mock = MagicMock()
        resolved_key_mock.is_valid = True
        resolved_key_mock.key_value = "keytest123"
        resolved_key_mock.source.value = "test"
        resolved_key_mock.masked_value = "********st123"
        
        # The resolver's get_api_key returns a context manager
        mock_resolver.get_api_key.return_value.__enter__.return_value = resolved_key_mock
        return mock_resolver

    @pytest.fixture
    def integrated_api_service(self, mock_current_user, mock_api_key_resolver):
        """Fixture to provide a mocked IntegratedAPIService instance."""
        with patch('src.security.auth.AuthManager.get_current_user', return_value=mock_current_user):
            service = IntegratedAPIService()
            service.resolver = mock_api_key_resolver
            yield service

    @pytest.fixture
    def mock_airtable_record(self):
        """Mock Airtable record object."""
        return {
            'id': 'rectest123',
            'fields': {
                'Date': '2024-08-17',
                'Amount': 100.50,
                'Category': 'Operating',
                'Description': 'Test cost',
                'Currency': 'USD'
            },
            'createdTime': '2024-08-17T12:00:00.000Z'
        }

    @patch('requests.Session.post')
    def test_create_record_success(self, mock_post, integrated_api_service, mock_airtable_record):
        """Test successful record creation."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_airtable_record

        with integrated_api_service.get_airtable_client() as (session, info):
            assert session is not None
            assert info['success'] is True
            
            record_data = {'fields': mock_airtable_record['fields']}
            response = session.post(AIRTABLE_API_URL, json=record_data)
            
            record = response.json()
            assert record['id'] == 'rectest123'
            assert record['fields']['Amount'] == 100.50
            mock_post.assert_called_once_with(AIRTABLE_API_URL, json=record_data)

    @patch('requests.Session.get')
    def test_get_record_success(self, mock_get, integrated_api_service, mock_airtable_record):
        """Test successful record retrieval."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_airtable_record

        with integrated_api_service.get_airtable_client() as (session, info):
            assert session is not None
            
            record_id = 'rectest123'
            response = session.get(f"{AIRTABLE_API_URL}/{record_id}")
            
            record = response.json()
            assert record['id'] == 'rectest123'
            assert record['fields']['Category'] == 'Operating'
            mock_get.assert_called_once_with(f"{AIRTABLE_API_URL}/{record_id}")

    @patch('requests.Session.patch')
    def test_update_record_success(self, mock_patch, integrated_api_service, mock_airtable_record):
        """Test successful record update."""
        updated_record = mock_airtable_record.copy()
        updated_record['fields']['Amount'] = 150.75
        
        mock_patch.return_value.status_code = 200
        mock_patch.return_value.json.return_value = updated_record

        with integrated_api_service.get_airtable_client() as (session, info):
            assert session is not None
            
            record_id = 'rectest123'
            update_data = {'fields': {'Amount': 150.75}}
            response = session.patch(f"{AIRTABLE_API_URL}/{record_id}", json=update_data)
            
            record = response.json()
            assert record['fields']['Amount'] == 150.75
            mock_patch.assert_called_once_with(f"{AIRTABLE_API_URL}/{record_id}", json=update_data)

    @patch('requests.Session.delete')
    def test_delete_record_success(self, mock_delete, integrated_api_service):
        """Test successful record deletion."""
        mock_delete.return_value.status_code = 200
        mock_delete.return_value.json.return_value = {'deleted': True, 'id': 'rectest123'}

        with integrated_api_service.get_airtable_client() as (session, info):
            assert session is not None
            
            record_id = 'rectest123'
            response = session.delete(f"{AIRTABLE_API_URL}/{record_id}")
            
            result = response.json()
            assert result['deleted'] is True
            mock_delete.assert_called_once_with(f"{AIRTABLE_API_URL}/{record_id}")

    @patch('requests.Session.get')
    def test_list_records_success(self, mock_get, integrated_api_service, mock_airtable_record):
        """Test successful records listing."""
        mock_records = {'records': [mock_airtable_record] * 3}
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_records

        with integrated_api_service.get_airtable_client() as (session, info):
            assert session is not None
            
            response = session.get(AIRTABLE_API_URL)
            
            records = response.json()['records']
            assert len(records) == 3
            assert all(r['fields']['Category'] == 'Operating' for r in records)
            mock_get.assert_called_once_with(AIRTABLE_API_URL, params=None)

    @patch('requests.Session.get')
    def test_list_records_with_filter(self, mock_get, integrated_api_service, mock_airtable_record):
        """Test records listing with a filter formula."""
        mock_records = {'records': [mock_airtable_record]}
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_records

        with integrated_api_service.get_airtable_client() as (session, info):
            assert session is not None
            
            filter_formula = "AND({Category} = 'Operating', {Amount} > 50)"
            params = {'filterByFormula': filter_formula}
            response = session.get(AIRTABLE_API_URL, params=params)
            
            records = response.json()['records']
            assert len(records) == 1
            mock_get.assert_called_once_with(AIRTABLE_API_URL, params=params)

    @patch('requests.Session.post')
    def test_api_failure_handling(self, mock_post, integrated_api_service):
        """Test that API failures are handled gracefully."""
        # The service's context manager now handles this.
        # We check that it returns None, and an error message.
        with patch('src.services.api_key_resolver.APIKeyResolver.get_api_key') as mock_get_key:
            # Simulate an invalid key
            mock_get_key.return_value.__enter__.return_value.is_valid = False
            mock_get_key.return_value.__enter__.return_value.error_message = "API key not found"
            
            with integrated_api_service.get_airtable_client() as (session, info):
                assert session is None
                assert "Airtable API key not found" in info['error']
