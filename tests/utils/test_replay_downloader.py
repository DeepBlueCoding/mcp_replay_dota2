"""
Test suite for replay_downloader.py

Following CLAUDE.md testing principles:
- Test against REAL EXPECTED VALUES from actual data
- Test business logic correctness with real inputs
- No framework behavior testing, only actual business value
"""


import pytest

from src.models.combat_log import DownloadReplayResponse
from src.utils.replay_downloader import ReplayDownloader

# Real test data - verified match ID that we have downloaded
REAL_MATCH_ID = 8461956309
EXPECTED_REPLAY_SIZE_MB_MIN = 350  # At least this size
EXPECTED_REPLAY_SIZE_MB_MAX = 450  # At most this size


class TestReplayDownloader:
    """Test suite for ReplayDownloader."""

    @pytest.fixture
    def downloader(self):
        return ReplayDownloader()

    def test_get_replay_path_returns_path_for_existing_replay(self, downloader):
        """Test that get_replay_path returns a Path for cached replays."""
        path = downloader.get_replay_path(REAL_MATCH_ID)

        # Replay MUST be available for tests
        assert path is not None, f"Replay {REAL_MATCH_ID} not cached locally"
        assert path.exists()
        assert path.suffix == ".dem"
        assert str(REAL_MATCH_ID) in path.name

    def test_get_replay_path_returns_none_for_nonexistent_replay(self, downloader):
        """Test that get_replay_path returns None for replays not in cache."""
        fake_match_id = 9999999999
        path = downloader.get_replay_path(fake_match_id)

        assert path is None

    def test_replay_size_is_reasonable(self, downloader):
        """Test that cached replay has expected file size."""
        path = downloader.get_replay_path(REAL_MATCH_ID)

        # Replay MUST be available for tests
        assert path is not None, f"Replay {REAL_MATCH_ID} not cached locally"

        size_mb = path.stat().st_size / (1024 * 1024)
        assert EXPECTED_REPLAY_SIZE_MB_MIN <= size_mb <= EXPECTED_REPLAY_SIZE_MB_MAX

    def test_list_replays_returns_dem_files(self, downloader):
        """Test that list_replays returns .dem files."""
        replays = downloader.list_replays()

        # All returned paths should be .dem files
        for replay in replays:
            assert replay.suffix == ".dem"


class TestDownloadReplayResponse:
    """Test suite for DownloadReplayResponse model."""

    def test_success_response_has_required_fields(self):
        """Test that a success response has all required fields populated."""
        response = DownloadReplayResponse(
            success=True,
            match_id=REAL_MATCH_ID,
            replay_path="/path/to/replay.dem",
            file_size_mb=398.0,
            already_cached=True,
        )

        assert response.success is True
        assert response.match_id == REAL_MATCH_ID
        assert response.replay_path == "/path/to/replay.dem"
        assert response.file_size_mb == 398.0
        assert response.already_cached is True
        assert response.error is None

    def test_error_response_has_error_message(self):
        """Test that an error response has the error field populated."""
        response = DownloadReplayResponse(
            success=False,
            match_id=REAL_MATCH_ID,
            error="Could not download replay",
        )

        assert response.success is False
        assert response.match_id == REAL_MATCH_ID
        assert response.replay_path is None
        assert response.file_size_mb is None
        assert response.already_cached is False
        assert response.error == "Could not download replay"
