# ruff: noqa: E402
"""
Reusable replay download and management functionality for MCP tools.
"""

import sys
from pathlib import Path
from typing import Optional, Tuple

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the working replay downloader directly

import opendota
import requests


class ReplayManager:
    """Manages replay downloading and file access for MCP tools."""

    def __init__(self, replays_dir: Optional[str] = None):
        """Initialize replay manager with configurable storage directory."""
        if replays_dir:
            self.replays_dir = Path(replays_dir)
        else:
            self.replays_dir = project_root / ".data" / "replays"

        # Ensure directory exists
        self.replays_dir.mkdir(parents=True, exist_ok=True)

        # Initialize OpenDota client
        self.client = opendota.OpenDota(delay=3)

    def get_replay_path(self, match_id: int) -> Path:
        """Get the expected file path for a replay."""
        return self.replays_dir / f"{match_id}.dem"

    async def download_replay(self, match_id: int, force_redownload: bool = False) -> Tuple[bool, str, Path]:
        """
        Download replay file if needed.

        Args:
            match_id: Dota 2 match ID
            force_redownload: Force re-download even if file exists

        Returns:
            Tuple of (success: bool, message: str, file_path: Path)
        """
        replay_path = self.get_replay_path(match_id)

        # Check if file already exists and we don't need to force redownload
        if replay_path.exists() and not force_redownload:
            file_size = replay_path.stat().st_size
            return True, f"Replay already exists ({file_size} bytes)", replay_path

        # Download the replay
        success = await self._download_match_replay(match_id)

        if success and replay_path.exists():
            file_size = replay_path.stat().st_size
            return True, f"Successfully downloaded replay ({file_size} bytes)", replay_path
        else:
            return False, f"Failed to download replay for match {match_id}", replay_path

    async def _get_replay_url(self, match_id: int) -> Optional[str]:
        """Get replay download URL from OpenDota API"""
        print(f"Fetching replay URL for match {match_id}...")

        match_data = await self.client.get_match(match_id)

        if not match_data:
            print(f"❌ Failed to get match data for {match_id}")
            return None

        replay_url = match_data.replay_url
        if not replay_url:
            print(f"❌ No replay URL available for match {match_id}")
            return None

        print(f"✓ Found replay URL: {replay_url}")
        return replay_url

    def _download_replay_file(self, match_id: int, replay_url: str) -> bool:
        """Download replay file from URL with progress tracking"""
        replay_path = self.replays_dir / f"{match_id}.dem"

        # Skip if already exists
        if replay_path.exists():
            print(f"✓ Replay already exists: {replay_path}")
            return True

        print(f"Downloading replay for match {match_id}...")

        response = requests.get(replay_url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(replay_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r  Progress: {progress:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)

        print(f"✓ Downloaded replay: {replay_path} ({downloaded} bytes)")
        return True

    async def _download_match_replay(self, match_id: int) -> bool:
        """Complete workflow to download a match replay"""
        print(f"\n=== DOWNLOADING REPLAY FOR MATCH {match_id} ===")

        # Get replay URL
        replay_url = await self._get_replay_url(match_id)
        if not replay_url:
            return False

        # Download the file
        success = self._download_replay_file(match_id, replay_url)
        if success:
            replay_path = self.replays_dir / f"{match_id}.dem"
            print(f"✅ Replay saved to: {replay_path}")

        return success


# Global instance for reuse across MCP tools
replay_manager = ReplayManager()


async def download_replay_for_mcp(match_id: int, force_redownload: bool = False) -> Tuple[bool, str, Path]:
    """
    Reusable function for MCP tools to download replays.

    Args:
        match_id: Dota 2 match ID
        force_redownload: Force re-download even if file exists

    Returns:
        Tuple of (success: bool, message: str, file_path: Path)
    """
    return await replay_manager.download_replay(match_id, force_redownload)


def get_replay_path_for_mcp(match_id: int) -> Path:
    """Get the file path where a replay should be stored."""
    return replay_manager.get_replay_path(match_id)
