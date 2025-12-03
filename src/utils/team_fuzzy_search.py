"""Fuzzy search utility for pro teams."""

import logging
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from src.models.pro_scene import SearchResult

logger = logging.getLogger(__name__)


class TeamFuzzySearch:
    """Fuzzy search for teams using OpenDota data and manual aliases."""

    def __init__(self):
        self._teams: List[Dict[str, Any]] = []
        self._aliases: Dict[str, List[str]] = {}
        self._initialized = False

    def initialize(
        self, teams: List[Dict[str, Any]], aliases: Dict[str, List[str]]
    ) -> None:
        """Initialize with team data and aliases."""
        self._teams = teams
        self._aliases = aliases
        self._initialized = True
        logger.info(
            f"Initialized team fuzzy search with {len(teams)} teams "
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

    def _get_searchable_names(self, team: Dict[str, Any]) -> List[str]:
        """Get all searchable names for a team."""
        names = []
        team_id = str(team.get("team_id", ""))

        if team.get("name"):
            names.append(team["name"])

        if team.get("tag"):
            names.append(team["tag"])

        if team_id in self._aliases:
            names.extend(self._aliases[team_id])

        return names

    def search(
        self, query: str, threshold: float = 0.6, max_results: int = 10
    ) -> List[SearchResult]:
        """
        Search for teams using fuzzy matching.

        Args:
            query: Search string (team name, tag, alias, etc.)
            threshold: Minimum similarity score (0.0-1.0)
            max_results: Maximum results to return

        Returns:
            List of SearchResult sorted by similarity
        """
        if not self._initialized:
            logger.warning("Team fuzzy search not initialized")
            return []

        if not query or not query.strip():
            return []

        matches = []

        for team in self._teams:
            team_id = team.get("team_id")
            if not team_id:
                continue

            team_name = team.get("name") or team.get("tag") or "Unknown"
            searchable_names = self._get_searchable_names(team)

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
                        id=team_id,
                        name=team_name,
                        matched_alias=matched_alias,
                        similarity=best_score,
                    )
                )

        matches.sort(key=lambda x: x.similarity, reverse=True)
        return matches[:max_results]

    def find_best_match(
        self, query: str, threshold: float = 0.6
    ) -> Optional[SearchResult]:
        """Find the single best matching team."""
        matches = self.search(query, threshold, max_results=1)
        return matches[0] if matches else None

    def find_team_by_name(
        self, query: str, threshold: float = 0.6
    ) -> Optional[Dict[str, Any]]:
        """Find team data by fuzzy name search."""
        match = self.find_best_match(query, threshold)
        if not match:
            return None

        for team in self._teams:
            if team.get("team_id") == match.id:
                return team

        return None

    def suggest(self, partial_name: str, max_suggestions: int = 10) -> List[str]:
        """Get team name suggestions for autocomplete."""
        if not partial_name or len(partial_name) < 2:
            return []

        matches = self.search(partial_name, threshold=0.3, max_results=max_suggestions)
        return [match.name for match in matches]


team_fuzzy_search = TeamFuzzySearch()
