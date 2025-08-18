"""
Cloud Secrets Manager Integration
Supports AWS Secrets Manager, Azure Key Vault, and local development
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class SecretProvider(str, Enum):
    """Secret provider types"""
    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    AZURE_KEY_VAULT = "azure_key_vault"
    LOCAL_ENV = "local_env"

class SecretVersion:
    """Secret version metadata"""
    def __init__(self, version_id: str, created_date: datetime, is_current: bool = False):
        self.version_id = version_id
        self.created_date = created_date
        self.is_current = is_current

class SecretsManager:
    """Universal secrets manager with cloud provider support"""
    
    def __init__(self, provider: SecretProvider = SecretProvider.LOCAL_ENV):
        self.provider = provider
        self.client = self._initialize_client()
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)
    
    def _initialize_client(self):
        """Initialize cloud provider client"""
        if self.provider == SecretProvider.AWS_SECRETS_MANAGER:
            try:
                return boto3.client('secretsmanager')
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Secrets Manager: {str(e)}")
                return None
        
        elif self.provider == SecretProvider.AZURE_KEY_VAULT:
            try:
                from azure.keyvault.secrets import SecretClient
                from azure.identity import DefaultAzureCredential
                
                vault_url = os.getenv('AZURE_KEY_VAULT_URL')
                if vault_url:
                    credential = DefaultAzureCredential()
                    return SecretClient(vault_url=vault_url, credential=credential)
            except ImportError:
                logger.warning("Azure Key Vault SDK not installed")
            except Exception as e:
                logger.warning(f"Failed to initialize Azure Key Vault: {str(e)}")
            return None
        
        return None  # Local environment doesn't need a client
    
    def get_secret(self, secret_name: str, version: Optional[str] = None) -> Optional[str]:
        """Get secret value with caching"""
        cache_key = f"{secret_name}:{version or 'current'}"
        
        # Check cache first
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < self.cache_ttl:
                return cached_data['value']
        
        # Fetch from provider
        secret_value = self._fetch_secret(secret_name, version)
        
        # Cache the result
        if secret_value:
            self.cache[cache_key] = {
                'value': secret_value,
                'timestamp': datetime.now()
            }
        
        return secret_value
    
    def _fetch_secret(self, secret_name: str, version: Optional[str] = None) -> Optional[str]:
        """Fetch secret from configured provider"""
        try:
            if self.provider == SecretProvider.AWS_SECRETS_MANAGER:
                return self._fetch_aws_secret(secret_name, version)
            
            elif self.provider == SecretProvider.AZURE_KEY_VAULT:
                return self._fetch_azure_secret(secret_name, version)
            
            else:  # LOCAL_ENV
                return os.getenv(secret_name)
                
        except Exception as e:
            logger.error(f"Failed to fetch secret {secret_name}: {str(e)}")
            return None
    
    def _fetch_aws_secret(self, secret_name: str, version: Optional[str] = None) -> Optional[str]:
        """Fetch secret from AWS Secrets Manager"""
        if not self.client:
            return None
        
        try:
            kwargs = {'SecretId': secret_name}
            if version:
                kwargs['VersionId'] = version
            
            response = self.client.get_secret_value(**kwargs)
            return response['SecretString']
            
        except ClientError as e:
            logger.error(f"AWS Secrets Manager error: {str(e)}")
            return None
    
    def _fetch_azure_secret(self, secret_name: str, version: Optional[str] = None) -> Optional[str]:
        """Fetch secret from Azure Key Vault"""
        if not self.client:
            return None
        
        try:
            if version:
                secret = self.client.get_secret(secret_name, version)
            else:
                secret = self.client.get_secret(secret_name)
            
            return secret.value
            
        except Exception as e:
            logger.error(f"Azure Key Vault error: {str(e)}")
            return None
    
    def set_secret(self, secret_name: str, secret_value: str, description: Optional[str] = None) -> bool:
        """Set or update secret value"""
        try:
            if self.provider == SecretProvider.AWS_SECRETS_MANAGER:
                return self._set_aws_secret(secret_name, secret_value, description)
            
            elif self.provider == SecretProvider.AZURE_KEY_VAULT:
                return self._set_azure_secret(secret_name, secret_value)
            
            else:  # LOCAL_ENV - can't set environment variables at runtime
                logger.warning("Cannot set secrets in LOCAL_ENV mode")
                return False
                
        except Exception as e:
            logger.error(f"Failed to set secret {secret_name}: {str(e)}")
            return False
    
    def _set_aws_secret(self, secret_name: str, secret_value: str, description: Optional[str] = None) -> bool:
        """Set secret in AWS Secrets Manager"""
        if not self.client:
            return False
        
        try:
            # Try to update existing secret
            self.client.update_secret(
                SecretId=secret_name,
                SecretString=secret_value,
                Description=description or f"Updated on {datetime.now().isoformat()}"
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Create new secret
                try:
                    self.client.create_secret(
                        Name=secret_name,
                        SecretString=secret_value,
                        Description=description or f"Created on {datetime.now().isoformat()}"
                    )
                    return True
                except ClientError as create_error:
                    logger.error(f"Failed to create AWS secret: {str(create_error)}")
                    return False
            else:
                logger.error(f"Failed to update AWS secret: {str(e)}")
                return False
    
    def _set_azure_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set secret in Azure Key Vault"""
        if not self.client:
            return False
        
        try:
            self.client.set_secret(secret_name, secret_value)
            return True
        except Exception as e:
            logger.error(f"Failed to set Azure secret: {str(e)}")
            return False
    
    def list_secrets(self) -> List[str]:
        """List all secret names"""
        try:
            if self.provider == SecretProvider.AWS_SECRETS_MANAGER:
                return self._list_aws_secrets()
            
            elif self.provider == SecretProvider.AZURE_KEY_VAULT:
                return self._list_azure_secrets()
            
            else:  # LOCAL_ENV
                # Return environment variables that look like secrets
                secret_patterns = ['API_KEY', 'SECRET', 'TOKEN', 'PASSWORD']
                return [
                    key for key in os.environ.keys()
                    if any(pattern in key.upper() for pattern in secret_patterns)
                ]
                
        except Exception as e:
            logger.error(f"Failed to list secrets: {str(e)}")
            return []
    
    def _list_aws_secrets(self) -> List[str]:
        """List AWS secrets"""
        if not self.client:
            return []
        
        try:
            response = self.client.list_secrets()
            return [secret['Name'] for secret in response['SecretList']]
        except ClientError as e:
            logger.error(f"Failed to list AWS secrets: {str(e)}")
            return []
    
    def _list_azure_secrets(self) -> List[str]:
        """List Azure Key Vault secrets"""
        if not self.client:
            return []
        
        try:
            secrets = self.client.list_properties_of_secrets()
            return [secret.name for secret in secrets]
        except Exception as e:
            logger.error(f"Failed to list Azure secrets: {str(e)}")
            return []
    
    def rotate_secret(self, secret_name: str, new_value: str) -> bool:
        """Rotate secret with versioning"""
        try:
            # Set new version
            if self.set_secret(secret_name, new_value, f"Rotated on {datetime.now().isoformat()}"):
                # Clear cache to force refresh
                self._clear_cache(secret_name)
                logger.info(f"Successfully rotated secret: {secret_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to rotate secret {secret_name}: {str(e)}")
            return False
    
    def delete_secret(self, secret_name: str, force: bool = False) -> bool:
        """Delete secret (with recovery period for AWS)"""
        try:
            if self.provider == SecretProvider.AWS_SECRETS_MANAGER:
                return self._delete_aws_secret(secret_name, force)
            
            elif self.provider == SecretProvider.AZURE_KEY_VAULT:
                return self._delete_azure_secret(secret_name)
            
            else:  # LOCAL_ENV
                logger.warning("Cannot delete environment variables")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete secret {secret_name}: {str(e)}")
            return False
    
    def _delete_aws_secret(self, secret_name: str, force: bool = False) -> bool:
        """Delete AWS secret"""
        if not self.client:
            return False
        
        try:
            kwargs = {'SecretId': secret_name}
            if force:
                kwargs['ForceDeleteWithoutRecovery'] = True
            else:
                kwargs['RecoveryWindowInDays'] = 7  # 7-day recovery window
            
            self.client.delete_secret(**kwargs)
            self._clear_cache(secret_name)
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete AWS secret: {str(e)}")
            return False
    
    def _delete_azure_secret(self, secret_name: str) -> bool:
        """Delete Azure Key Vault secret"""
        if not self.client:
            return False
        
        try:
            self.client.begin_delete_secret(secret_name)
            self._clear_cache(secret_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete Azure secret: {str(e)}")
            return False
    
    def get_secret_versions(self, secret_name: str) -> List[SecretVersion]:
        """Get all versions of a secret"""
        try:
            if self.provider == SecretProvider.AWS_SECRETS_MANAGER:
                return self._get_aws_secret_versions(secret_name)
            
            elif self.provider == SecretProvider.AZURE_KEY_VAULT:
                return self._get_azure_secret_versions(secret_name)
            
            else:  # LOCAL_ENV
                # Environment variables don't have versions
                return [SecretVersion("current", datetime.now(), True)]
                
        except Exception as e:
            logger.error(f"Failed to get secret versions for {secret_name}: {str(e)}")
            return []
    
    def _get_aws_secret_versions(self, secret_name: str) -> List[SecretVersion]:
        """Get AWS secret versions"""
        if not self.client:
            return []
        
        try:
            response = self.client.list_secret_version_ids(SecretId=secret_name)
            versions = []
            
            for version in response['Versions']:
                versions.append(SecretVersion(
                    version_id=version['VersionId'],
                    created_date=version['CreatedDate'],
                    is_current='AWSCURRENT' in version.get('VersionStages', [])
                ))
            
            return sorted(versions, key=lambda x: x.created_date, reverse=True)
            
        except ClientError as e:
            logger.error(f"Failed to get AWS secret versions: {str(e)}")
            return []
    
    def _get_azure_secret_versions(self, secret_name: str) -> List[SecretVersion]:
        """Get Azure Key Vault secret versions"""
        if not self.client:
            return []
        
        try:
            versions = []
            secret_versions = self.client.list_properties_of_secret_versions(secret_name)
            
            for version in secret_versions:
                versions.append(SecretVersion(
                    version_id=version.version,
                    created_date=version.created_on,
                    is_current=version.enabled
                ))
            
            return sorted(versions, key=lambda x: x.created_date, reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get Azure secret versions: {str(e)}")
            return []
    
    def _clear_cache(self, secret_name: str) -> None:
        """Clear cache entries for a secret"""
        keys_to_remove = [key for key in self.cache.keys() if key.startswith(f"{secret_name}:")]
        for key in keys_to_remove:
            del self.cache[key]
    
    def emergency_revoke_all(self) -> Dict[str, bool]:
        """Emergency revocation of all secrets (for security incidents)"""
        logger.critical("EMERGENCY SECRET REVOCATION INITIATED")
        
        results = {}
        secrets = self.list_secrets()
        
        for secret_name in secrets:
            try:
                # For emergency revocation, we delete the secret
                success = self.delete_secret(secret_name, force=True)
                results[secret_name] = success
                
                if success:
                    logger.critical(f"Emergency revoked secret: {secret_name}")
                else:
                    logger.error(f"Failed to emergency revoke secret: {secret_name}")
                    
            except Exception as e:
                logger.error(f"Error during emergency revocation of {secret_name}: {str(e)}")
                results[secret_name] = False
        
        # Clear all cache
        self.cache.clear()
        
        return results
