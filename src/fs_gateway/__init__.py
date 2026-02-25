"""Filesystem gateway with OAuth3 scope gates."""

from .fs_gateway_service import (
    FSAccessError,
    FSPathError,
    FSScopeError,
    FilesystemGatewayService,
)

__all__ = [
    "FSAccessError",
    "FSPathError",
    "FSScopeError",
    "FilesystemGatewayService",
]
