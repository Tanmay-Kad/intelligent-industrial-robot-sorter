#!/usr/bin/env python3
"""
Intelligent Industrial Object Sorting System
Verification Script: Python to CoppeliaSim ZMQ Remote API Connection
"""

import sys
import time

def verify_connection(host='localhost', port=23000):
    print("=" * 60)
    print(" CoppeliaSim ZMQ Remote API - Connection Test")
    print("=" * 60)
    print(f"[*] Target host : {host}")
    print(f"[*] Target port : {port}")
    print("[*] Initializing RemoteAPIClient...")

    try:
        from coppeliasim_zmqremoteapi_client import RemoteAPIClient
    except ImportError as e:
        print("\n[!] ERROR: 'coppeliasim-zmqremoteapi-client' is not installed.")
        print("    Run: pip install coppeliasim-zmqremoteapi-client")
        return False

    try:
        # Create client instance connecting to ZMQ server
        client = RemoteAPIClient(host=host, port=port)
        
        # Retrieve the simulation object
        sim = client.require('sim')
        
        # Query simulation details
        sim_time = sim.getSimulationTime()
        sim_state = sim.getSimulationState()
        version_int = sim.getInt32Param(sim.intparam_program_version)
        major = version_int // 10000
        minor = (version_int % 10000) // 100
        patch = version_int % 100
        version_str = f"{major}.{minor}.{patch}"

        state_names = {
            sim.simulation_stopped: "STOPPED",
            sim.simulation_paused: "PAUSED",
            sim.simulation_advancing_firstafterstop: "STARTING",
            sim.simulation_advancing_running: "RUNNING",
            sim.simulation_advancing_lastbeforestop: "STOPPING"
        }
        state_str = state_names.get(sim_state, f"UNKNOWN ({sim_state})")

        print("\n" + "-" * 60)
        print(" [SUCCESS] Successfully connected to CoppeliaSim!")
        print("-" * 60)
        print(f" [+] CoppeliaSim Version : {version_str} (raw: {version_int})")
        print(f" [+] Simulation State   : {state_str}")
        print(f" [+] Simulation Time    : {sim_time:.3f} s")
        print("-" * 60)
        print(" Python <-> CoppeliaSim communication is active and verified.\n")
        return True

    except Exception as err:
        print("\n" + "!" * 60)
        print(" [FAILURE] Failed to connect to CoppeliaSim ZMQ server.")
        print("!" * 60)
        print(f" Details: {err}")
        print("\nTroubleshooting Checklist:")
        print(" 1. Ensure CoppeliaSim Edu is running.")
        print(" 2. Confirm the ZMQ Remote API server is active in CoppeliaSim (default port 23000).")
        print(" 3. Check Windows Firewall or antivirus if local loopback communication is blocked.")
        return False


if __name__ == "__main__":
    success = verify_connection()
    sys.exit(0 if success else 1)
