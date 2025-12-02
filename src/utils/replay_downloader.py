import bz2
import logging
from pathlib import Path
from typing import Optional

import requests
from opendota import OpenDota

logger = logging.getLogger(__name__)


class ReplayDownloader:
    """Utility class to download and extract Dota 2 replay files."""

    def __init__(self, replay_dir: Optional[str] = None):
        """
        Initialize the replay downloader.

        Args:
            replay_dir: Directory to store replays. Defaults to ~/dota2/replays
        """
        if replay_dir:
            self.replay_dir = Path(replay_dir)
        else:
            self.replay_dir = Path.home() / "dota2" / "replays"

        # Create directory if it doesn't exist
        self.replay_dir.mkdir(parents=True, exist_ok=True)

        # Initialize OpenDota client with json format to get raw data
        self.opendota = OpenDota(format='json')

    async def download_replay(self, match_id: int, force: bool = False) -> Optional[Path]:
        """
        Download and extract a replay file for the given match ID.

        Args:
            match_id: The match ID to download replay for
            force: Force download even if file already exists

        Returns:
            Path to the extracted .dem file, or None if download failed
        """
        dem_file = self.replay_dir / f"{match_id}.dem"

        # Check if file already exists
        if dem_file.exists() and not force:
            logger.info(f"Replay for match {match_id} already exists at {dem_file}")
            return dem_file

        # Get match details with replay URL
        try:
            match = await self.opendota.get_match(match_id)
            replay_url = match.get('replay_url')

            if not replay_url:
                logger.error(f"No replay URL available for match {match_id}")
                return None

            # Download the bz2 file
            bz2_file = self._download_bz2(match_id, replay_url)
            if not bz2_file:
                return None

            # Extract the dem file
            extracted_file = self._extract_bz2(bz2_file, dem_file)

            # Clean up bz2 file
            if extracted_file and bz2_file.exists():
                bz2_file.unlink()
                logger.info(f"Removed temporary bz2 file: {bz2_file}")

            return extracted_file

        except Exception as e:
            logger.error(f"Failed to download replay for match {match_id}: {e}")
            return None
        finally:
            # Close the client connection
            await self.opendota.close()

    def _download_bz2(self, match_id: int, url: str) -> Optional[Path]:
        """
        Download the bz2 compressed replay file.

        Args:
            match_id: The match ID
            url: The replay URL

        Returns:
            Path to the downloaded bz2 file, or None if download failed
        """
        bz2_file = self.replay_dir / f"{match_id}.dem.bz2"

        try:
            logger.info(f"Downloading replay from {url}")

            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Get total file size for progress tracking
            total_size = int(response.headers.get('content-length', 0))

            # Download with progress
            downloaded = 0
            chunk_size = 8192

            with open(bz2_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if downloaded % (chunk_size * 100) == 0:  # Log every ~800KB
                                logger.info(f"Download progress: {progress:.1f}%")

            logger.info(f"Successfully downloaded replay to {bz2_file}")
            return bz2_file

        except requests.RequestException as e:
            logger.error(f"Failed to download replay: {e}")
            # Clean up partial download
            if bz2_file.exists():
                bz2_file.unlink()
            return None

    def _extract_bz2(self, bz2_file: Path, output_file: Path) -> Optional[Path]:
        """
        Extract a bz2 compressed file.

        Args:
            bz2_file: Path to the bz2 file
            output_file: Path for the extracted file

        Returns:
            Path to the extracted file, or None if extraction failed
        """
        try:
            logger.info(f"Extracting {bz2_file} to {output_file}")

            with bz2.open(bz2_file, 'rb') as f_in:
                with open(output_file, 'wb') as f_out:
                    # Read and write in chunks for memory efficiency
                    chunk_size = 1024 * 1024  # 1MB chunks
                    while True:
                        chunk = f_in.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)

            logger.info(f"Successfully extracted replay to {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to extract bz2 file: {e}")
            # Clean up partial extraction
            if output_file.exists():
                output_file.unlink()
            return None

    def get_replay_path(self, match_id: int) -> Optional[Path]:
        """
        Get the path to a replay file if it exists.

        Args:
            match_id: The match ID

        Returns:
            Path to the replay file if it exists, None otherwise
        """
        dem_file = self.replay_dir / f"{match_id}.dem"
        return dem_file if dem_file.exists() else None

    def list_replays(self) -> list[Path]:
        """
        List all available replay files.

        Returns:
            List of paths to replay files
        """
        return list(self.replay_dir.glob("*.dem"))

    def delete_replay(self, match_id: int) -> bool:
        """
        Delete a replay file.

        Args:
            match_id: The match ID

        Returns:
            True if file was deleted, False if file didn't exist
        """
        dem_file = self.replay_dir / f"{match_id}.dem"
        if dem_file.exists():
            dem_file.unlink()
            logger.info(f"Deleted replay file: {dem_file}")
            return True
        return False

    def get_replay_size(self, match_id: int) -> Optional[int]:
        """
        Get the size of a replay file in bytes.

        Args:
            match_id: The match ID

        Returns:
            Size in bytes, or None if file doesn't exist
        """
        dem_file = self.replay_dir / f"{match_id}.dem"
        return dem_file.stat().st_size if dem_file.exists() else None

