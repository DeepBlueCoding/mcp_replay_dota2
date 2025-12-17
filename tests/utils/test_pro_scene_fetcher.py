"""Tests for pro_scene_fetcher utility functions."""

from src.utils.pro_scene_fetcher import pro_scene_fetcher


class TestSignatureHeroes:
    """Tests for signature heroes data loading."""

    def test_load_signature_heroes_data(self):
        """Test that signature heroes data can be loaded from file."""
        data = pro_scene_fetcher.get_player_signature_heroes()

        assert isinstance(data, dict)
        assert len(data) > 0

    def test_signature_heroes_excludes_metadata(self):
        """Test that metadata keys starting with _ are excluded."""
        data = pro_scene_fetcher.get_player_signature_heroes()

        for key in data:
            assert not key.startswith("_")

    def test_yatoro_signature_heroes(self):
        """Test Yatoro's signature heroes are correctly loaded."""
        data = pro_scene_fetcher.get_player_signature_heroes()
        yatoro = data.get("311360822")

        assert yatoro is not None
        assert yatoro["name"] == "Yatoro"
        assert yatoro["role"] == 1
        assert "npc_dota_hero_morphling" in yatoro["signature_heroes"]
        assert "npc_dota_hero_slark" in yatoro["signature_heroes"]

    def test_collapse_signature_heroes(self):
        """Test Collapse's signature heroes as pos 3."""
        data = pro_scene_fetcher.get_player_signature_heroes()
        collapse = data.get("113331514")

        assert collapse is not None
        assert collapse["name"] == "Collapse"
        assert collapse["role"] == 3
        assert "npc_dota_hero_mars" in collapse["signature_heroes"]
        assert "npc_dota_hero_magnataur" in collapse["signature_heroes"]

    def test_miposhka_signature_heroes(self):
        """Test Miposhka's signature heroes as pos 5."""
        data = pro_scene_fetcher.get_player_signature_heroes()
        miposhka = data.get("139876032")

        assert miposhka is not None
        assert miposhka["name"] == "Miposhka"
        assert miposhka["role"] == 5
        assert len(miposhka["signature_heroes"]) >= 3

    def test_pure_signature_heroes(self):
        """Test Pure's signature heroes as pos 1."""
        data = pro_scene_fetcher.get_player_signature_heroes()
        pure = data.get("168803634")

        assert pure is not None
        assert pure["name"] == "Pure"
        assert pure["role"] == 1
        assert "npc_dota_hero_faceless_void" in pure["signature_heroes"]
        assert "npc_dota_hero_terrorblade" in pure["signature_heroes"]
