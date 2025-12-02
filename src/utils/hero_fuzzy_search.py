"""
Fuzzy hero search utility using simplified heroes data and constants integration.
"""

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional

from src.resources.heroes_resources import heroes_resource


class HeroFuzzySearch:
    """Fuzzy search for heroes using simplified data, then fetch full data from constants."""

    def __init__(self):
        """Initialize fuzzy search with heroes data."""
        self._fuzzy_data = {}
        self._load_fuzzy_data()

    def _load_fuzzy_data(self):
        """Load simplified heroes data for fuzzy searching."""
        fuzzy_file = Path(__file__).parent.parent.parent / "data" / "heroes_fuzzy.json"

        if not fuzzy_file.exists():
            raise FileNotFoundError(f"Heroes fuzzy search data not found: {fuzzy_file}")

        with open(fuzzy_file, 'r') as f:
            self._fuzzy_data = json.load(f)

    def _calculate_similarity(self, search_term: str, alias: str) -> float:
        """Calculate similarity between search term and alias."""
        search_lower = search_term.lower().strip()
        alias_lower = alias.lower().strip()

        # Exact match gets highest score
        if search_lower == alias_lower:
            return 1.0

        # Check if search term is contained in alias or vice versa
        if search_lower in alias_lower:
            return 0.9
        elif alias_lower in search_lower:
            return 0.8

        # Use sequence matcher for fuzzy matching
        return SequenceMatcher(None, search_lower, alias_lower).ratio()

    def search_heroes(self, search_term: str, threshold: float = 0.6, max_results: int = 5) -> List[Dict]:
        """
        Search for heroes using fuzzy matching on names and aliases.

        Args:
            search_term: The search string (hero name, alias, etc.)
            threshold: Minimum similarity score (0.0-1.0)
            max_results: Maximum number of results to return

        Returns:
            List of hero matches with similarity scores, sorted by relevance
        """
        if not search_term or not search_term.strip():
            return []

        matches = []

        for hero_key, hero_data in self._fuzzy_data.items():
            best_score = 0.0
            matched_alias = ""

            # Check hero name
            name_score = self._calculate_similarity(search_term, hero_data['name'])
            if name_score > best_score:
                best_score = name_score
                matched_alias = hero_data['name']

            # Check all aliases
            for alias in hero_data['aliases']:
                alias_score = self._calculate_similarity(search_term, alias)
                if alias_score > best_score:
                    best_score = alias_score
                    matched_alias = alias

            # Add to matches if above threshold
            if best_score >= threshold:
                matches.append({
                    'hero_key': hero_key,
                    'hero_id': hero_data['hero_id'],
                    'name': hero_data['name'],
                    'matched_alias': matched_alias,
                    'similarity': best_score
                })

        # Sort by similarity score (descending) and limit results
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        return matches[:max_results]

    def find_best_match(self, search_term: str, threshold: float = 0.6) -> Optional[Dict]:
        """
        Find the single best match for a search term.

        Args:
            search_term: The search string
            threshold: Minimum similarity score

        Returns:
            Best matching hero data or None if no match above threshold
        """
        matches = self.search_heroes(search_term, threshold, max_results=1)
        return matches[0] if matches else None

    def get_hero_by_fuzzy_name(self, search_term: str, threshold: float = 0.6) -> Optional[Dict]:
        """
        Find hero by fuzzy name search and return full hero data from constants.

        Args:
            search_term: The search string
            threshold: Minimum similarity score

        Returns:
            Full hero data from constants or None if no match
        """
        match = self.find_best_match(search_term, threshold)
        if not match:
            return None

        # Get full hero data from constants using the matched hero_id
        hero_id = match['hero_id']
        full_hero_data = heroes_resource.constants.convert_hero_by_id(hero_id)

        if full_hero_data:
            # Add fuzzy match metadata
            full_hero_data['_fuzzy_match'] = {
                'search_term': search_term,
                'matched_alias': match['matched_alias'],
                'similarity': match['similarity']
            }

        return full_hero_data

    def get_heroes_by_fuzzy_names(self, search_terms: List[str], threshold: float = 0.6) -> List[Dict]:
        """
        Find multiple heroes by fuzzy name search.

        Args:
            search_terms: List of search strings
            threshold: Minimum similarity score

        Returns:
            List of full hero data from constants
        """
        results = []
        for term in search_terms:
            hero_data = self.get_hero_by_fuzzy_name(term, threshold)
            if hero_data:
                results.append(hero_data)

        return results

    def suggest_heroes(self, partial_name: str, max_suggestions: int = 10) -> List[str]:
        """
        Get hero name suggestions for autocomplete.

        Args:
            partial_name: Partial hero name
            max_suggestions: Maximum suggestions to return

        Returns:
            List of suggested hero names
        """
        if not partial_name or len(partial_name) < 2:
            return []

        matches = self.search_heroes(partial_name, threshold=0.3, max_results=max_suggestions)
        return [match['name'] for match in matches]


# Global fuzzy search instance
hero_fuzzy_search = HeroFuzzySearch()
