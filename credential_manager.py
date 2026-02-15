#!/usr/bin/env python3
"""
SECURE CREDENTIAL MANAGER
Loads credentials from environment variables (not plaintext files)

Usage:
    from credential_manager import CredentialManager

    creds = CredentialManager.get_credentials('gmail')
    email = creds['email']
    password = creds['password']

Setup:
    export GMAIL_EMAIL="your-email@gmail.com"
    export GMAIL_PASSWORD="your-app-password"
    export LINKEDIN_EMAIL="your-email@linkedin.com"
    export LINKEDIN_PASSWORD="your-password"
"""

import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class CredentialManager:
    """Secure credential loading from environment variables"""

    # Mapping of service -> required env vars
    CREDENTIAL_SPECS = {
        'gmail': {
            'email': 'GMAIL_EMAIL',
            'password': 'GMAIL_PASSWORD',
        },
        'linkedin': {
            'email': 'LINKEDIN_EMAIL',
            'password': 'LINKEDIN_PASSWORD',
        },
        'google': {
            'email': 'GOOGLE_EMAIL',
            'password': 'GOOGLE_PASSWORD',
        }
    }

    @classmethod
    def get_credentials(cls, service: str) -> Dict[str, str]:
        """
        Load credentials for a service from environment variables.

        Args:
            service: Service name (gmail, linkedin, google, etc.)

        Returns:
            Dictionary of credentials {field: value}

        Raises:
            EnvironmentError: If required env vars are not set
        """
        if service not in cls.CREDENTIAL_SPECS:
            raise ValueError(f"Unknown service: {service}")

        spec = cls.CREDENTIAL_SPECS[service]
        credentials = {}

        for field, env_var in spec.items():
            value = os.getenv(env_var)
            if not value:
                raise EnvironmentError(
                    f"Missing required environment variable: {env_var}\n"
                    f"\nTo set up credentials, run:\n"
                    f"  export {env_var}=\"your-{field}\"\n"
                    f"\nFor Gmail, use an app password (not regular password):\n"
                    f"  https://myaccount.google.com/apppasswords"
                )
            credentials[field] = value

        logger.info(f"✅ Loaded {service} credentials from environment")
        return credentials

    @classmethod
    def validate_all(cls) -> bool:
        """Validate all configured services have credentials"""
        missing = []

        for service, spec in cls.CREDENTIAL_SPECS.items():
            for field, env_var in spec.items():
                if not os.getenv(env_var):
                    missing.append(f"{env_var} (for {service}.{field})")

        if missing:
            logger.warning(f"⚠️  Missing credentials: {', '.join(missing)}")
            return False

        logger.info(f"✅ All credentials validated")
        return True

    @classmethod
    def get_safe_debug_info(cls) -> Dict[str, str]:
        """Get debug info without exposing actual credentials"""
        info = {}

        for service, spec in cls.CREDENTIAL_SPECS.items():
            service_info = {}
            for field, env_var in spec.items():
                value = os.getenv(env_var)
                if value:
                    # Show only first/last char for safety
                    masked = value[0] + "***" + value[-1] if len(value) > 2 else "***"
                    service_info[field] = f"{env_var}={masked}"
                else:
                    service_info[field] = f"{env_var}=NOT SET"
            info[service] = service_info

        return info


if __name__ == '__main__':
    # Test credential loading
    logging.basicConfig(level=logging.INFO)

    print("=== Credential Manager Test ===\n")

    try:
        creds = CredentialManager.get_credentials('gmail')
        print(f"✅ Gmail credentials loaded")
    except EnvironmentError as e:
        print(f"❌ {e}")

    print("\nDebug info:")
    for service, info in CredentialManager.get_safe_debug_info().items():
        print(f"  {service}: {info}")
