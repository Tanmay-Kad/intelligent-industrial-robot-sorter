"""
Centralized ZeroMQ Remote API Client for CoppeliaSim
"""

import sys
from typing import Tuple, Any

try:
    from coppeliasim_zmqremoteapi_client import RemoteAPIClient
except ImportError:
    RemoteAPIClient = None


def get_sim_client(host: str = "localhost", port: int = 23000) -> Tuple[Any, Any]:
    """
    Connects to the CoppeliaSim ZeroMQ Remote API server.
    
    Returns:
        tuple: (client, sim) where client is RemoteAPIClient and sim is the simulation object.
    
    Raises:
        RuntimeError: If connection fails or client library is missing.
    """
    if RemoteAPIClient is None:
        raise RuntimeError(
            "coppeliasim-zmqremoteapi-client package is not installed.\n"
            "Install it via: pip install coppeliasim-zmqremoteapi-client"
        )
    
    try:
        client = RemoteAPIClient(host=host, port=port)
        sim = client.require("sim")
        return client, sim
    except Exception as err:
        raise RuntimeError(
            f"Failed to connect to CoppeliaSim at {host}:{port}.\n"
            f"Error: {err}\n"
            "Please verify that CoppeliaSim is running and the ZMQ Remote API is enabled."
        ) from err
