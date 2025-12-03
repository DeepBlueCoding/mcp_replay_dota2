"""Fuzzy search utility for pro players."""

import logging
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from src.models.pro_scene import SearchResult

logger = logging.getLogger(__name__)


class PlayerFuzzySearch:
    """Fuzzy search for pro players using OpenDota data and manual aliases."""

    def __init__(self):
        self._players: List[Dict[str, Any]] = []
        self._aliases: Dict[str, List[str]] = {}
        self._initialized = False

    def initialize(
        self, players: List[Dict[str, Any]], aliases: Dict[str, List[str]]
    ) -> None:
        """Initialize with player data and aliases."""
        self._players = players
        self._aliases = aliases
        self._initialized = True
        logger.info(
            f"Initialized player fuzzy search with {len(players)} players "
            f"and {len(aliases)} alias entries"
        )

    def _calculate_similarity(self, search_term: str, target: str) -> float:
        """Calculate similarity between search term and target string."""
        search_lower = search_term.lower().strip()
        target_lower = target.lower().strip()

        if search_lower == target_lower:
            return 1.0

        if search_lower in target_lower:
            return 0.9
        elif target_lower in search_lower:
            return 0.8

        return SequenceMatcher(None, search_lower, target_lower).ratio()

    def _get_searchable_names(self, player: Dict[str, Any]) -> List[str]:
        """Get all searchable names for a player."""
        names = []
        account_id = str(player.get("account_id", ""))

        if player.get("name"):
            names.append(player["name"])

        if player.get("personaname"):
            names.append(player["personaname"])

        if account_id in self._aliases:
            names.extend(self._aliases[account_id])

        return names

    def search(
        self, query: str, threshold: float = 0.6, max_results: int = 10
    ) -> List[SearchResult]:
        """
        Search for players using fuzzy matching.

        Args:
            query: Search string (player name, alias, etc.)
            threshold: Minimum similarity score (0.0-1.0)
            max_results: Maximum results to return

        Returns:
            List of SearchResult sorted by similarity
        """
        if not self._initialized:
            logger.warning("Player fuzzy search not initialized")
            return []

        if not query or not query.strip():
            return []

        matches = []

        for player in self._players:
            account_id = player.get("account_id")
            if not account_id:
                continue

            player_name = player.get("name") or player.get("personaname") or "Unknown"
            searchable_names = self._get_searchable_names(player)

            best_score = 0.0
            matched_alias = ""

            for name in searchable_names:
                if not name:
                    continue
                score = self._calculate_similarity(query, name)
                if score > best_score:
                    best_score = score
                    matched_alias = name

            if best_score >= threshold:
                matches.append(
                    SearchResult(
                        id=account_id,
                        name=player_name,
                        matched_alias=matched_alias,
                        similarity=best_score,
                    )
                )

        matches.sort(key=lambda x: x.similarity, reverse=True)
        return matches[:max_results]

    def find_best_match(
        self, query: str, threshold: float = 0.6
    ) -> Optional[SearchResult]:
        """Find the single best matching player."""
        matches = self.search(query, threshold, max_results=1)
        return matches[0] if matches else None

    def find_player_by_name(
        self, query: str, threshold: float = 0.6
    ) -> Optional[Dict[str, Any]]:
        """Find player data by fuzzy name search."""
        match = self.find_best_match(query, threshold)
        if not match:
            return None

        for player in self._players:
            if player.get("account_id") == match.id:
                return player

        return None

    def suggest(self, partial_name: str, max_suggestions: int = 10) -> List[str]:
        """Get player name suggestions for autocomplete."""
        if not partial_name or len(partial_name) < 2:
            return []

        matches = self.search(partial_name, threshold=0.3, max_results=max_suggestions)
        return [match.name for match in matches]


player_fuzzy_search = PlayerFuzzySearch()
