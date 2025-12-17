"""
Main replay service for downloading, parsing, and caching replay data.

Uses python-manta v2 for single-pass parsing with progress callbacks.
NO MCP DEPENDENCIES - progress is reported via callback protocol.
"""

import bz2
import logging
import os
from pathlib import Path
from typing import Optional

import requests
from opendota import OpenDota
from python_manta import CombatLogType, Parser

from ..cache.replay_cache import ReplayCache
from ..models.replay_data import ParsedReplayData, ProgressCallback

logger = logging.getLogger(__name__)


def _get_default_replay_dir() -> Path:
    """Get replay directory, checking DOTA_REPLAY_CACHE env var first."""
    if env_cache := os.environ.get("DOTA_REPLAY_CACHE"):
        return Path(env_cache).expanduser()
    return Path.home() / "dota2" / "replays"


DEFAULT_REPLAY_DIR = _get_default_replay_dir()


class ReplayService:
    """
    Main service for replay data access.

    Handles:
    - Downloading replays from OpenDota
    - Parsing with python-manta v2 (single-pass)
    - Caching parsed data
    - Progress reporting via callbacks

    NO MCP DEPENDENCIES - can be used from any interface.
    """

    def __init__(
        self,
        cache: Optional[ReplayCache] = None,
        replay_dir: Optional[Path] = None,
    ):
        """Initialize the replay service.

        Args:
            cache: ReplayCache instance. Creates default if not provided.
            replay_dir: Directory for replay files. Defaults to ~/dota2/replays
        """
        self._cache = cache or ReplayCache()
        self._replay_dir = replay_dir or DEFAULT_REPLAY_DIR
        self._replay_dir.mkdir(parents=True, exist_ok=True)

    async def get_parsed_data(
        self,
        match_id: int,
        progress: Optional[ProgressCallback] = None,
    ) -> ParsedReplayData:
        """Get complete parsed data for a match.

        Returns cached data if available, otherwise downloads and parses.

        Args:
            match_id: The match ID
            progress: Optional callback for progress updates

        Returns:
            ParsedReplayData with all extracted data

        Raises:
            ValueError: If replay cannot be downloaded or parsed
        """
        # Check cache first
        if progress:
            await progress(0, 100, "Checking cache...")

        cached = self._cache.get(match_id)
        if cached:
            if progress:
                await progress(100, 100, "Loaded from cache")
            return cached

        # Download replay
        if progress:
            await progress(5, 100, "Downloading replay (this may take 30-60s)...")

        replay_path = await self._download_replay(match_id, progress)
        if not replay_path:
            raise ValueError(f"Could not download replay for match {match_id}")

        # Parse replay
        if progress:
            await progress(50, 100, "Parsing replay...")

        try:
            data = self._parse_replay(match_id, replay_path, progress)
        except ValueError as e:
            # Parsing failed - delete corrupt replay so it can be re-downloaded
            logger.error(f"Parsing failed for match {match_id}, deleting corrupt replay: {e}")
            if replay_path.exists():
                replay_path.unlink()
            raise ValueError(f"Replay file corrupt, deleted for re-download: {e}")

        # Cache result
        if progress:
            await progress(95, 100, "Caching results...")

        self._cache.set(match_id, data)

        if progress:
            await progress(100, 100, "Complete")

        return data

    async def download_only(
        self,
        match_id: int,
        progress: Optional[ProgressCallback] = None,
    ) -> Path:
        """Download replay without parsing.

        Use this to pre-download replays for later analysis.

        Args:
            match_id: The match ID
            progress: Optional callback for progress updates

        Returns:
            Path to the downloaded .dem file

        Raises:
            ValueError: If replay cannot be downloaded
        """
        # Check if already downloaded
        existing = self._get_replay_path(match_id)
        if existing:
            if progress:
                await progress(100, 100, "Replay already downloaded")
            return existing

        # Download
        replay_path = await self._download_replay(match_id, progress)
        if not replay_path:
            raise ValueError(f"Could not download replay for match {match_id}")

        return replay_path

    def is_cached(self, match_id: int) -> bool:
        """Check if match data is cached."""
        return self._cache.has(match_id)

    def is_downloaded(self, match_id: int) -> bool:
        """Check if replay file is downloaded."""
        return self._get_replay_path(match_id) is not None

    def _get_replay_path(self, match_id: int) -> Optional[Path]:
        """Get path to replay if it exists and is valid size."""
        dem_file = self._replay_dir / f"{match_id}.dem"
        if not dem_file.exists():
            return None

        # Validate file size (min 10MB for valid replay)
        min_size = 10 * 1024 * 1024  # 10 MB
        file_size = dem_file.stat().st_size
        if file_size < min_size:
            logger.warning(f"Replay {match_id} too small ({file_size} bytes), deleting")
            dem_file.unlink()
            return None

        return dem_file

    async def _download_replay(
        self,
        match_id: int,
        progress: Optional[ProgressCallback] = None,
    ) -> Optional[Path]:
        """Download and extract replay file."""
        dem_file = self._replay_dir / f"{match_id}.dem"

        # Check if already exists
        if dem_file.exists():
            logger.info(f"Replay for match {match_id} already exists")
            return dem_file

        # Get replay URL from OpenDota
        opendota = OpenDota(format='json')
        try:
            if progress:
                await progress(10, 100, "Getting replay URL from OpenDota...")

            match = await opendota.get_match(match_id)
            replay_url = match.get('replay_url')

            if not replay_url:
                logger.error(f"No replay URL for match {match_id}")
                return None

            # Download bz2 file
            bz2_file = await self._download_bz2(match_id, replay_url, progress)
            if not bz2_file:
                return None

            # Extract
            if progress:
                await progress(45, 100, "Extracting replay...")

            extracted = self._extract_bz2(bz2_file, dem_file)

            # Cleanup bz2
            if extracted and bz2_file.exists():
                bz2_file.unlink()

            return extracted

        except Exception as e:
            logger.error(f"Failed to download replay for match {match_id}: {e}")
            return None
        finally:
            await opendota.close()

    async def _download_bz2(
        self,
        match_id: int,
        url: str,
        progress: Optional[ProgressCallback] = None,
    ) -> Optional[Path]:
        """Download compressed replay file with progress."""
        bz2_file = self._replay_dir / f"{match_id}.dem.bz2"

        try:
            logger.info(f"Downloading replay from {url}")

            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 65536  # 64KB chunks

            with open(bz2_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress and total_size > 0:
                            # Map download progress to 10-40% range
                            pct = 10 + int((downloaded / total_size) * 30)
                            mb_done = downloaded / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            await progress(
                                pct, 100,
                                f"Downloading... {mb_done:.1f}/{mb_total:.1f} MB"
                            )

            # Verify download completed
            if total_size > 0 and downloaded != total_size:
                logger.error(f"Incomplete download: got {downloaded} bytes, expected {total_size}")
                if bz2_file.exists():
                    bz2_file.unlink()
                return None

            logger.info(f"Downloaded replay to {bz2_file} ({downloaded} bytes)")
            return bz2_file

        except requests.RequestException as e:
            logger.error(f"Failed to download replay: {e}")
            if bz2_file.exists():
                bz2_file.unlink()
            return None

    def _extract_bz2(self, bz2_file: Path, output_file: Path) -> Optional[Path]:
        """Extract bz2 compressed file."""
        try:
            logger.info(f"Extracting {bz2_file}")

            with bz2.open(bz2_file, 'rb') as f_in:
                with open(output_file, 'wb') as f_out:
                    chunk_size = 1024 * 1024  # 1MB chunks
                    while True:
                        chunk = f_in.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)

            # Verify extracted file is reasonable size (min 10MB for valid replay)
            file_size = output_file.stat().st_size
            min_size = 10 * 1024 * 1024  # 10 MB
            if file_size < min_size:
                logger.error(f"Extracted file too small: {file_size} bytes (min {min_size})")
                if output_file.exists():
                    output_file.unlink()
                return None

            logger.info(f"Extracted replay to {output_file} ({file_size / (1024*1024):.1f} MB)")
            return output_file

        except Exception as e:
            logger.error(f"Failed to extract bz2: {e}")
            if output_file.exists():
                output_file.unlink()
            return None

    def _parse_replay(
        self,
        match_id: int,
        replay_path: Path,
        progress: Optional[ProgressCallback] = None,
    ) -> ParsedReplayData:
        """Parse replay with python-manta v2 single-pass API."""
        replay_str = str(replay_path)

        parser = Parser(replay_str)

        # Single-pass parse with all collectors
        logger.info(f"Parsing replay {replay_path}")

        # Build parse config - attacks is optional (requires python-manta 1.4.5.4+)
        parse_config = {
            "header": True,
            "game_info": True,
            "combat_log": {
                "types": [
                    CombatLogType.DAMAGE.value,
                    CombatLogType.HEAL.value,
                    CombatLogType.MODIFIER_ADD.value,
                    CombatLogType.MODIFIER_REMOVE.value,
                    CombatLogType.DEATH.value,
                    CombatLogType.ABILITY.value,
                    CombatLogType.ITEM.value,
                    CombatLogType.PURCHASE.value,
                    CombatLogType.ABILITY_TRIGGER.value,
                    CombatLogType.NEUTRAL_CAMP_STACK.value,
                    CombatLogType.PICKUP_RUNE.value,
                ],
                "max_entries": 100000,
            },
            "entities": {
                "interval_ticks": 900,  # ~30 second snapshots
                "max_snapshots": 200,
            },
            "game_events": {
                "max_events": 10000,
            },
            "modifiers": {
                "max_modifiers": 50000,
            },
            "messages": {
                "message_types": ['CDOTAMatchMetadataFile'],
                "max_messages": 0,  # No limit - need to find metadata at end of file
            },
        }

        # Check if attacks collector is available (python-manta 1.4.5.4+)
        import inspect
        parse_sig = inspect.signature(parser.parse)
        if 'attacks' in parse_sig.parameters:
            parse_config["attacks"] = {
                "max_events": 50000,  # Capture attacks for neutral aggro/tower pressure
            }
            logger.info("Attacks collector enabled")
        else:
            logger.info("Attacks collector not available (requires python-manta 1.4.5.4+)")

        # Check if entity_deaths collector is available (python-manta 1.4.5.4+)
        if 'entity_deaths' in parse_sig.parameters:
            parse_config["entity_deaths"] = {
                "creeps_only": True,  # Only track creep deaths for wave detection
                "max_events": 10000,
            }
            logger.info("Entity deaths collector enabled")
        else:
            logger.info("Entity deaths collector not available (requires python-manta 1.4.5.4+)")

        result = parser.parse(**parse_config)

        if not result.success:
            raise ValueError(f"Parsing failed: {result.error}")

        # Extract metadata from messages (CDOTAMatchMetadataFile for timeline data)
        metadata = self._extract_metadata_from_result(result)

        logger.info(f"Parsed {len(result.combat_log.entries) if result.combat_log else 0} combat log entries")
        logger.info(f"Parsed {len(result.entities.snapshots) if result.entities else 0} entity snapshots")
        if hasattr(result, 'attacks') and result.attacks:
            logger.info(f"Parsed {len(result.attacks.events)} attack events")
        if hasattr(result, 'entity_deaths') and result.entity_deaths:
            logger.info(f"Parsed {len(result.entity_deaths.events)} entity death events")

        return ParsedReplayData.from_parse_result(
            match_id=match_id,
            replay_path=replay_str,
            result=result,
            metadata=metadata,
            demo_index=None,  # Will be added in Phase 4
        )

    def _extract_metadata_from_result(self, result) -> Optional[dict]:
        """Extract CDOTAMatchMetadataFile from parse result messages."""
        try:
            if result.messages and result.messages.messages:
                for msg in result.messages.messages:
                    if msg.type == 'CDOTAMatchMetadataFile':
                        logger.info("Found CDOTAMatchMetadataFile metadata")
                        return msg.data
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
        return None

    def get_replay_file_size(self, match_id: int) -> Optional[float]:
        """Get replay file size in MB."""
        path = self._get_replay_path(match_id)
        if path:
            return path.stat().st_size / (1024 * 1024)
        return None

    def delete_replay(self, match_id: int) -> bool:
        """Delete replay file and cache entry."""
        # Delete file
        path = self._get_replay_path(match_id)
        if path:
            path.unlink()

        # Delete cache
        return self._cache.delete(match_id)
