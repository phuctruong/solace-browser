#!/usr/bin/env python3

"""
Solace Browser HTTP Bridge - Python Wrapper for CLI Commands

Bridges HTTP requests to Solace Browser CLI commands
Parses CLI output to JSON
Handles errors gracefully
Logs to Cloud Logging (Google Cloud)
Records metrics (execution time, status, cost)

Auth: 65537 | Northstar: Phuc Forecast
"""

import asyncio
import json
import hashlib
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum

try:
    import httpx
    from pydantic import BaseModel, Field
except ImportError:
    print("Error: Required packages not installed. Install with:")
    print("  pip install httpx pydantic google-cloud-logging")
    sys.exit(1)

try:
    from google.cloud import logging as cloud_logging
except ImportError:
    cloud_logging = None

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT = os.getenv('PROJECT_ROOT', '/app')
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, 'artifacts')
RECIPES_DIR = os.path.join(PROJECT_ROOT, 'data', 'default', 'recipes')
EPISODES_DIR = os.path.join(PROJECT_ROOT, 'episodes')
CLI_SCRIPT = os.path.join(PROJECT_ROOT, 'solace-browser-cli-v2.sh')
BROWSER_PATH = os.getenv('BROWSER_PATH', '/usr/local/bin/solace-browser')
MAX_EXECUTION_TIME = int(os.getenv('MAX_EXECUTION_TIME', 3600))  # 1 hour
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', '')

# ============================================================================
# Logging Setup
# ============================================================================

def setup_logging():
    """Configure logging with optional Cloud Logging integration"""
    log_level = logging.DEBUG if DEBUG else logging.INFO

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)

    # Logger
    logger = logging.getLogger('solace-http-bridge')
    logger.setLevel(log_level)
    logger.addHandler(console_handler)

    # Cloud Logging integration (optional)
    if cloud_logging and GCP_PROJECT_ID:
        try:
            cloud_handler = cloud_logging.CloudLoggingHandler()
            cloud_handler.setLevel(log_level)
            logger.addHandler(cloud_handler)
            logger.info('Cloud Logging initialized for project: %s', GCP_PROJECT_ID)
        except (ImportError, OSError, ValueError) as e:
            logger.warning('Failed to initialize Cloud Logging: %s', str(e))

    return logger

logger = setup_logging()

# ============================================================================
# Data Models
# ============================================================================

class ControlMode(str, Enum):
    """Browser control modes"""
    REAL = 'real'
    MOCK = 'mock'
    HTTP_API = 'http_api'


class ExecutionStatus(str, Enum):
    """Execution status codes"""
    SUCCESS = 'success'
    FAILURE = 'failure'
    TIMEOUT = 'timeout'
    INVALID = 'invalid'


class EpisodeModel(BaseModel):
    """Episode data model"""
    episode_id: str
    timestamp: str
    url: str
    status: str
    control_mode: ControlMode
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    snapshots: List[Dict[str, Any]] = Field(default_factory=list)


class RecipeModel(BaseModel):
    """Recipe data model"""
    recipe_id: str
    timestamp: str
    source_episode: str
    source_hash: str
    control_mode: ControlMode
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    status: str
    locked: bool = True
    version: str = '1.0'


class ProofArtifact(BaseModel):
    """Proof artifact model"""
    proof_id: str
    timestamp: str
    recipe_id: str
    status: ExecutionStatus
    execution_time: float
    actions_executed: int
    execution_trace: Optional[str] = None
    errors: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class Metric(BaseModel):
    """Cloud Monitoring metric"""
    metric_name: str
    value: float
    timestamp: str
    labels: Dict[str, str] = Field(default_factory=dict)


# ============================================================================
# HTTP Bridge Client
# ============================================================================

class SolaceBrowserBridge:
    """HTTP client for Solace Browser API"""

    def __init__(self, base_url: str = 'http://localhost:8080'):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=MAX_EXECUTION_TIME
        )
        self.metrics: List[Metric] = []

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def health_check(self) -> bool:
        """Check if API is healthy"""
        try:
            response = await self.client.get('/health')
            return response.status_code == 200
        except (httpx.HTTPError, OSError, ConnectionError) as e:
            logger.error('Health check failed: %s', str(e))
            return False

    async def get_info(self) -> Dict[str, Any]:
        """Get server info"""
        try:
            response = await self.client.get('/info')
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error('Failed to get info: %s', str(e))
            raise

    async def start_episode(self, name: str, url: str = 'about:blank') -> Dict[str, Any]:
        """Start episode recording"""
        start_time = time.time()
        try:
            response = await self.client.post(
                f'/episode/start/{name}',
                json={'url': url}
            )
            response.raise_for_status()
            result = response.json()
            self._record_metric('episode_start', 1.0, {'episode_name': name})
            logger.info('Episode started: %s', name)
            return result
        except httpx.HTTPError as e:
            logger.error('Failed to start episode %s: %s', name, str(e))
            raise
        finally:
            self._record_execution_metric('episode_start', time.time() - start_time)

    async def stop_episode(self, name: str) -> Dict[str, Any]:
        """Stop episode recording"""
        start_time = time.time()
        try:
            response = await self.client.post(f'/episode/stop/{name}')
            response.raise_for_status()
            result = response.json()
            self._record_metric('episode_stop', 1.0, {'episode_name': name})
            logger.info('Episode stopped: %s', name)
            return result
        except httpx.HTTPError as e:
            logger.error('Failed to stop episode %s: %s', name, str(e))
            raise
        finally:
            self._record_execution_metric('episode_stop', time.time() - start_time)

    async def compile_recipe(self, recipe_name: str, episode_name: str) -> Dict[str, Any]:
        """Compile episode to recipe"""
        start_time = time.time()
        try:
            response = await self.client.post(
                f'/recipe/{recipe_name}/compile',
                json={'episode_name': episode_name}
            )
            response.raise_for_status()
            result = response.json()
            self._record_metric('recipe_compile', 1.0, {'recipe_name': recipe_name})
            logger.info('Recipe compiled: %s from %s', recipe_name, episode_name)
            return result
        except httpx.HTTPError as e:
            logger.error('Failed to compile recipe %s: %s', recipe_name, str(e))
            raise
        finally:
            self._record_execution_metric('recipe_compile', time.time() - start_time)

    async def execute_recipe(self, recipe_name: str) -> Dict[str, Any]:
        """Execute recipe"""
        start_time = time.time()
        try:
            response = await self.client.post(f'/recipe/{recipe_name}/execute')
            response.raise_for_status()
            result = response.json()
            self._record_metric('recipe_execute', 1.0, {'recipe_name': recipe_name})
            logger.info('Recipe executed: %s', recipe_name)
            return result
        except httpx.HTTPError as e:
            logger.error('Failed to execute recipe %s: %s', recipe_name, str(e))
            raise
        finally:
            self._record_execution_metric('recipe_execute', time.time() - start_time)

    async def execute_batch(self, recipes: List[str]) -> Dict[str, Any]:
        """Execute multiple recipes"""
        start_time = time.time()
        try:
            response = await self.client.post(
                '/recipes/execute-batch',
                json={'recipes': recipes}
            )
            response.raise_for_status()
            result = response.json()
            self._record_metric('batch_execute', float(len(recipes)))
            logger.info('Batch execution complete: %d recipes', len(recipes))
            return result
        except httpx.HTTPError as e:
            logger.error('Failed to execute batch: %s', str(e))
            raise
        finally:
            self._record_execution_metric('batch_execute', time.time() - start_time)

    async def get_artifact(self, artifact_id: str) -> Dict[str, Any]:
        """Get artifact"""
        try:
            response = await self.client.get(f'/artifacts/{artifact_id}')
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error('Failed to get artifact %s: %s', artifact_id, str(e))
            raise

    def _record_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Record a metric"""
        metric = Metric(
            metric_name=metric_name,
            value=value,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            labels=labels or {}
        )
        self.metrics.append(metric)
        logger.debug('Metric recorded: %s = %f', metric_name, value)

    def _record_execution_metric(self, operation: str, duration: float):
        """Record execution time metric"""
        self._record_metric(
            f'{operation}_duration_seconds',
            duration,
            {'operation': operation}
        )

    async def export_metrics(self) -> str:
        """Export metrics as JSON"""
        return json.dumps([m.dict() for m in self.metrics], indent=2)


# ============================================================================
# CLI Command Executor
# ============================================================================

class CLIExecutor:
    """Execute Solace Browser CLI commands"""

    def __init__(self, cli_path: str = CLI_SCRIPT):
        self.cli_path = cli_path
        self.execution_count = 0
        self.total_execution_time = 0.0

    async def execute(self, command: str, args: List[str] = None) -> Dict[str, Any]:
        """Execute a CLI command"""
        args = args or []
        start_time = time.time()

        try:
            # Prepare command
            cmd = [self.cli_path, command] + args

            logger.debug('Executing: %s', ' '.join(cmd))

            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=MAX_EXECUTION_TIME
            )

            execution_time = time.time() - start_time
            self.execution_count += 1
            self.total_execution_time += execution_time

            result = {
                'status': ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.FAILURE,
                'returncode': process.returncode,
                'stdout': stdout.decode('utf-8', errors='replace'),
                'stderr': stderr.decode('utf-8', errors='replace'),
                'execution_time': execution_time
            }

            logger.info(
                'Command executed: %s (returncode=%d, time=%.2fs)',
                command,
                process.returncode,
                execution_time
            )

            return result

        except asyncio.TimeoutError:
            logger.error('Command timeout: %s', command)
            return {
                'status': ExecutionStatus.TIMEOUT,
                'error': f'Command timed out after {MAX_EXECUTION_TIME} seconds',
                'execution_time': time.time() - start_time
            }
        except (OSError, ValueError, RuntimeError) as e:
            logger.error('Command failed: %s - %s', command, str(e))
            return {
                'status': ExecutionStatus.FAILURE,
                'error': str(e),
                'execution_time': time.time() - start_time
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        avg_time = (self.total_execution_time / self.execution_count
                    if self.execution_count > 0 else 0)
        return {
            'total_commands': self.execution_count,
            'total_time': self.total_execution_time,
            'average_time': avg_time
        }


# ============================================================================
# Utility Functions
# ============================================================================

def ensure_directories():
    """Ensure required directories exist"""
    dirs = [LOG_DIR, ARTIFACTS_DIR, RECIPES_DIR, EPISODES_DIR]
    for directory in dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.debug('Directory ready: %s', directory)


def parse_cli_output(output: str) -> Dict[str, Any]:
    """Parse CLI output to JSON"""
    try:
        # Try to extract JSON
        import re
        json_match = re.search(r'\{.*\}', output, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {'raw_output': output}
    except json.JSONDecodeError:
        return {'raw_output': output, 'parse_error': 'Could not parse JSON'}
    except (ValueError, AttributeError) as e:
        return {'raw_output': output, 'error': str(e)}


def hash_content(content: str) -> str:
    """Generate SHA256 hash of content"""
    return hashlib.sha256(content.encode()).hexdigest()


# ============================================================================
# Main Example Usage
# ============================================================================

async def main():
    """Example usage of the HTTP bridge"""
    ensure_directories()

    # Initialize bridge
    bridge = SolaceBrowserBridge()

    try:
        # Check health
        is_healthy = await bridge.health_check()
        print(f'API Health: {is_healthy}')

        if is_healthy:
            # Get info
            info = await bridge.get_info()
            print(f'API Info: {json.dumps(info, indent=2)}')

            # Example: Start episode
            # result = await bridge.start_episode('test-episode', 'https://example.com')
            # print(f'Episode started: {json.dumps(result, indent=2)}')

    except (httpx.HTTPError, OSError, ConnectionError, ValueError) as e:
        logger.error('Error: %s', str(e))
    finally:
        await bridge.close()


if __name__ == '__main__':
    # Create event loop and run main
    asyncio.run(main())
