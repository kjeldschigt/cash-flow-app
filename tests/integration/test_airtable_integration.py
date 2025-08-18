"""
Integration tests for Airtable service with mocked responses
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.services.integration_service import AirtableService
from models.cost import Cost

@pytest.mark.integration
class TestAirtableIntegration:
    """Test Airtable service integration with mocked API responses"""
    
    @pytest.fixture
    def airtable_service(self):
        """Create AirtableService instance with test configuration"""
        return AirtableService(
            api_key="keytest123",
            base_id="apptest123",
            table_name="Costs"
        )
    
    @pytest.fixture
    def mock_airtable_record(self):
        """Mock Airtable record object"""
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
    
    def test_create_record_success(self, airtable_service, mock_airtable_record):
        """Test successful record creation"""
        with patch('pyairtable.Table.create') as mock_create:
            mock_create.return_value = mock_airtable_record
            
            record_data = {
                'Date': '2024-08-17',
                'Amount': 100.50,
                'Category': 'Operating'
            }
            
            record = airtable_service.create_record(record_data)
            
            assert record['id'] == 'rectest123'
            assert record['fields']['Amount'] == 100.50
            mock_create.assert_called_once_with(record_data)
    
    def test_get_record_success(self, airtable_service, mock_airtable_record):
        """Test successful record retrieval"""
        with patch('pyairtable.Table.get') as mock_get:
            mock_get.return_value = mock_airtable_record
            
            record = airtable_service.get_record('rectest123')
            
            assert record['id'] == 'rectest123'
            assert record['fields']['Category'] == 'Operating'
            mock_get.assert_called_once_with('rectest123')
    
    def test_update_record_success(self, airtable_service, mock_airtable_record):
        """Test successful record update"""
        updated_record = mock_airtable_record.copy()
        updated_record['fields']['Amount'] = 150.75
        
        with patch('pyairtable.Table.update') as mock_update:
            mock_update.return_value = updated_record
            
            update_data = {'Amount': 150.75}
            record = airtable_service.update_record('rectest123', update_data)
            
            assert record['fields']['Amount'] == 150.75
            mock_update.assert_called_once_with('rectest123', update_data)
    
    def test_delete_record_success(self, airtable_service):
        """Test successful record deletion"""
        with patch('pyairtable.Table.delete') as mock_delete:
            mock_delete.return_value = {'deleted': True, 'id': 'rectest123'}
            
            result = airtable_service.delete_record('rectest123')
            
            assert result['deleted'] == True
            mock_delete.assert_called_once_with('rectest123')
    
    def test_list_records_success(self, airtable_service, mock_airtable_record):
        """Test successful records listing"""
        mock_records = [mock_airtable_record] * 3
        
        with patch('pyairtable.Table.all') as mock_all:
            mock_all.return_value = mock_records
            
            records = airtable_service.list_records()
            
            assert len(records) == 3
            assert all(record['fields']['Category'] == 'Operating' for record in records)
            mock_all.assert_called_once()
    
    def test_list_records_with_filter(self, airtable_service, mock_airtable_record):
        """Test records listing with filter formula"""
        filtered_records = [mock_airtable_record]
        
        with patch('pyairtable.Table.all') as mock_all:
            mock_all.return_value = filtered_records
            
            filter_formula = "AND({Category} = 'Operating', {Amount} > 50)"
            records = airtable_service.list_records(filter_formula=filter_formula)
            
            assert len(records) == 1
            mock_all.assert_called_once_with(formula=filter_formula)
    
    def test_sync_costs_to_airtable(self, airtable_service, sample_costs):
        """Test syncing local costs to Airtable"""
        with patch('pyairtable.Table.batch_create') as mock_batch_create:
            mock_batch_create.return_value = [{'id': f'rec{i}'} for i in range(len(sample_costs))]
            
            synced_count = airtable_service.sync_costs_to_airtable(sample_costs)
            
            assert synced_count == len(sample_costs)
            mock_batch_create.assert_called_once()
    
    def test_sync_airtable_to_costs(self, airtable_service, mock_airtable_record):
        """Test syncing Airtable records to local costs"""
        mock_records = [mock_airtable_record] * 5
        
        with patch('pyairtable.Table.all') as mock_all:
            mock_all.return_value = mock_records
            
            with patch('services.storage.add_cost') as mock_add_cost:
                synced_count = airtable_service.sync_airtable_to_costs()
                
                assert synced_count == 5
                assert mock_add_cost.call_count == 5
    
    def test_batch_operations_success(self, airtable_service):
        """Test batch create/update operations"""
        batch_data = [
            {'Date': '2024-08-17', 'Amount': 100, 'Category': 'Operating'},
            {'Date': '2024-08-18', 'Amount': 200, 'Category': 'Marketing'}
        ]
        
        mock_results = [{'id': 'rec1'}, {'id': 'rec2'}]
        
        with patch('pyairtable.Table.batch_create') as mock_batch:
            mock_batch.return_value = mock_results
            
            results = airtable_service.batch_create_records(batch_data)
            
            assert len(results) == 2
            mock_batch.assert_called_once_with(batch_data)
    
    def test_error_handling_api_failure(self, airtable_service):
        """Test error handling for API failures"""
        with patch('pyairtable.Table.create') as mock_create:
            mock_create.side_effect = Exception("API rate limit exceeded")
            
            with pytest.raises(Exception, match="API rate limit exceeded"):
                airtable_service.create_record({'Amount': 100})
    
    def test_error_handling_invalid_record_id(self, airtable_service):
        """Test error handling for invalid record ID"""
        with patch('pyairtable.Table.get') as mock_get:
            mock_get.side_effect = Exception("Record not found")
            
            with pytest.raises(Exception, match="Record not found"):
                airtable_service.get_record('invalid_id')
    
    def test_field_validation(self, airtable_service):
        """Test field validation before sending to Airtable"""
        # Valid data should pass
        valid_data = {
            'Date': '2024-08-17',
            'Amount': 100.50,
            'Category': 'Operating'
        }
        
        assert airtable_service.validate_record_data(valid_data) == True
        
        # Invalid data should fail
        invalid_data = {
            'Date': 'invalid-date',
            'Amount': 'not-a-number'
        }
        
        assert airtable_service.validate_record_data(invalid_data) == False

@pytest.mark.integration
class TestAirtableWebhooks:
    """Test Airtable webhook handling"""
    
    @pytest.fixture
    def airtable_service(self):
        return AirtableService(
            api_key="keytest123",
            base_id="apptest123",
            table_name="Costs"
        )
    
    def test_webhook_record_created(self, airtable_service):
        """Test handling record created webhook"""
        webhook_payload = {
            'timestamp': '2024-08-17T12:00:00.000Z',
            'base': {'id': 'apptest123'},
            'webhook': {'id': 'achtest123'},
            'changedTablesById': {
                'tbltest123': {
                    'changedRecordsById': {
                        'rectest123': {
                            'current': {
                                'cellValuesByFieldId': {
                                    'fldAmount': 100.50,
                                    'fldCategory': 'Operating'
                                }
                            },
                            'previous': None
                        }
                    }
                }
            }
        }
        
        with patch('services.storage.add_cost') as mock_add:
            result = airtable_service.handle_webhook(webhook_payload)
            
            assert result == True
            mock_add.assert_called_once()
    
    def test_webhook_record_updated(self, airtable_service):
        """Test handling record updated webhook"""
        webhook_payload = {
            'timestamp': '2024-08-17T12:00:00.000Z',
            'base': {'id': 'apptest123'},
            'changedTablesById': {
                'tbltest123': {
                    'changedRecordsById': {
                        'rectest123': {
                            'current': {
                                'cellValuesByFieldId': {
                                    'fldAmount': 150.75
                                }
                            },
                            'previous': {
                                'cellValuesByFieldId': {
                                    'fldAmount': 100.50
                                }
                            }
                        }
                    }
                }
            }
        }
        
        with patch('services.storage.update_cost') as mock_update:
            result = airtable_service.handle_webhook(webhook_payload)
            
            assert result == True
            mock_update.assert_called_once()
    
    def test_webhook_record_deleted(self, airtable_service):
        """Test handling record deleted webhook"""
        webhook_payload = {
            'timestamp': '2024-08-17T12:00:00.000Z',
            'base': {'id': 'apptest123'},
            'changedTablesById': {
                'tbltest123': {
                    'changedRecordsById': {
                        'rectest123': {
                            'current': None,
                            'previous': {
                                'cellValuesByFieldId': {
                                    'fldAmount': 100.50
                                }
                            }
                        }
                    }
                }
            }
        }
        
        with patch('services.storage.delete_cost') as mock_delete:
            result = airtable_service.handle_webhook(webhook_payload)
            
            assert result == True
            mock_delete.assert_called_once()

@pytest.mark.integration
@pytest.mark.performance
class TestAirtablePerformance:
    """Test Airtable service performance"""
    
    @pytest.fixture
    def airtable_service(self):
        return AirtableService(
            api_key="keytest123",
            base_id="apptest123",
            table_name="Costs"
        )
    
    def test_bulk_record_creation_performance(self, airtable_service, performance_monitor):
        """Test performance of creating multiple records"""
        batch_data = [
            {'Amount': i, 'Category': 'Operating', 'Date': '2024-08-17'}
            for i in range(100)
        ]
        
        mock_results = [{'id': f'rec{i}'} for i in range(100)]
        
        with patch('pyairtable.Table.batch_create') as mock_batch:
            mock_batch.return_value = mock_results
            
            performance_monitor.start()
            
            results = airtable_service.batch_create_records(batch_data)
            
            performance_monitor.assert_max_duration(2.0)
            assert len(results) == 100
    
    def test_large_dataset_sync_performance(self, airtable_service, performance_monitor):
        """Test performance of syncing large datasets"""
        mock_records = [
            {
                'id': f'rec{i}',
                'fields': {
                    'Amount': i * 10,
                    'Category': 'Operating',
                    'Date': '2024-08-17'
                }
            }
            for i in range(1000)
        ]
        
        with patch('pyairtable.Table.all') as mock_all:
            mock_all.return_value = mock_records
            
            with patch('services.storage.add_cost') as mock_add:
                performance_monitor.start()
                
                synced_count = airtable_service.sync_airtable_to_costs()
                
                performance_monitor.assert_max_duration(5.0)
                assert synced_count == 1000
