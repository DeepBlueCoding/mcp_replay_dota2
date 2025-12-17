"""
Tests for python-manta attack collector integration.

Verifies attack data from both ranged (TE_Projectile) and melee (combat log) sources.
Uses match 8461956309 as primary test fixture.
"""



class TestAttackCollectorAvailability:
    """Tests that attack collector data is available."""

    def test_attacks_data_exists(self, parsed_replay_data):
        """Attacks data should be populated from replay."""
        assert parsed_replay_data.attacks is not None
        assert hasattr(parsed_replay_data.attacks, 'events')

    def test_attacks_has_events(self, parsed_replay_data):
        """Attacks should have many events."""
        assert len(parsed_replay_data.attacks.events) > 10000

    def test_attacks_has_total_events(self, parsed_replay_data):
        """Attacks should report total_events count."""
        assert parsed_replay_data.attacks.total_events > 10000


class TestAttackEventFields:
    """Tests for AttackEvent field population."""

    def test_attack_has_game_time(self, parsed_replay_data):
        """Attack events have game_time."""
        event = parsed_replay_data.attacks.events[0]
        assert hasattr(event, 'game_time')
        assert isinstance(event.game_time, float)

    def test_attack_has_game_time_str(self, parsed_replay_data):
        """Attack events have game_time_str."""
        event = parsed_replay_data.attacks.events[100]
        assert hasattr(event, 'game_time_str')
        assert isinstance(event.game_time_str, str)

    def test_attack_has_attacker_name(self, parsed_replay_data):
        """Attack events have attacker_name."""
        event = parsed_replay_data.attacks.events[0]
        assert hasattr(event, 'attacker_name')
        assert isinstance(event.attacker_name, str)

    def test_attack_has_target_name(self, parsed_replay_data):
        """Attack events have target_name."""
        event = parsed_replay_data.attacks.events[0]
        assert hasattr(event, 'target_name')

    def test_attack_has_is_melee_flag(self, parsed_replay_data):
        """Attack events have is_melee flag."""
        event = parsed_replay_data.attacks.events[0]
        assert hasattr(event, 'is_melee')
        assert isinstance(event.is_melee, bool)

    def test_attack_has_source_index(self, parsed_replay_data):
        """Attack events have source_index."""
        event = parsed_replay_data.attacks.events[0]
        assert hasattr(event, 'source_index')
        assert isinstance(event.source_index, int)


class TestMeleeAndRangedAttacks:
    """Tests for melee and ranged attack separation."""

    def test_has_melee_attacks(self, parsed_replay_data):
        """Should have melee attacks in the data."""
        melee = [a for a in parsed_replay_data.attacks.events if a.is_melee]
        assert len(melee) > 1000

    def test_has_ranged_attacks(self, parsed_replay_data):
        """Should have ranged attacks in the data."""
        ranged = [a for a in parsed_replay_data.attacks.events if not a.is_melee]
        assert len(ranged) > 1000

    def test_melee_attacks_have_damage(self, parsed_replay_data):
        """Melee attacks should have damage values."""
        melee = [a for a in parsed_replay_data.attacks.events if a.is_melee]
        with_damage = [a for a in melee if a.damage > 0]
        assert len(with_damage) > 100

    def test_ranged_attacks_have_projectile_speed(self, parsed_replay_data):
        """Ranged attacks should have projectile_speed."""
        ranged = [a for a in parsed_replay_data.attacks.events if not a.is_melee]
        with_speed = [a for a in ranged if a.projectile_speed > 0]
        assert len(with_speed) > 100


class TestHeroNamingConsistency:
    """Tests for hero naming consistency (single underscore)."""

    def test_hero_attacks_have_single_underscore(self, parsed_replay_data):
        """Hero names should use single underscores, not double."""
        hero_attacks = [
            a for a in parsed_replay_data.attacks.events
            if "npc_dota_hero" in a.attacker_name
        ]
        for attack in hero_attacks[:100]:
            assert "__" not in attack.attacker_name, f"Double underscore in: {attack.attacker_name}"

    def test_shadow_demon_has_single_underscore(self, parsed_replay_data):
        """Shadow Demon should be shadow_demon not shadow__demon."""
        sd_attacks = [
            a for a in parsed_replay_data.attacks.events
            if "shadow" in a.attacker_name.lower() and "demon" in a.attacker_name.lower()
        ]
        if sd_attacks:
            assert "shadow_demon" in sd_attacks[0].attacker_name
            assert "shadow__demon" not in sd_attacks[0].attacker_name

    def test_naga_siren_has_single_underscore(self, parsed_replay_data):
        """Naga Siren should be naga_siren not naga__siren."""
        naga_attacks = [
            a for a in parsed_replay_data.attacks.events
            if "naga" in a.attacker_name.lower() and "siren" in a.attacker_name.lower()
        ]
        if naga_attacks:
            assert "naga_siren" in naga_attacks[0].attacker_name
            assert "naga__siren" not in naga_attacks[0].attacker_name


class TestHeroAttacks:
    """Tests for specific hero attack patterns in match 8461956309."""

    def test_juggernaut_has_melee_attacks(self, parsed_replay_data):
        """Juggernaut (melee carry) should have melee attacks."""
        jug_attacks = [
            a for a in parsed_replay_data.attacks.events
            if "juggernaut" in a.attacker_name.lower()
        ]
        melee_jug = [a for a in jug_attacks if a.is_melee]
        assert len(melee_jug) > 100

    def test_medusa_has_ranged_attacks(self, parsed_replay_data):
        """Medusa (ranged carry) should have ranged attacks."""
        medusa_attacks = [
            a for a in parsed_replay_data.attacks.events
            if "medusa" in a.attacker_name.lower()
        ]
        ranged_medusa = [a for a in medusa_attacks if not a.is_melee]
        assert len(ranged_medusa) > 100

    def test_nevermore_has_ranged_attacks(self, parsed_replay_data):
        """Nevermore/Shadow Fiend (ranged mid) should have ranged attacks."""
        sf_attacks = [
            a for a in parsed_replay_data.attacks.events
            if "nevermore" in a.attacker_name.lower()
        ]
        ranged_sf = [a for a in sf_attacks if not a.is_melee]
        assert len(ranged_sf) > 50

    def test_earthshaker_has_melee_attacks(self, parsed_replay_data):
        """Earthshaker (melee support) should have melee attacks."""
        es_attacks = [
            a for a in parsed_replay_data.attacks.events
            if "earthshaker" in a.attacker_name.lower()
        ]
        melee_es = [a for a in es_attacks if a.is_melee]
        assert len(melee_es) > 10


class TestAttackTargets:
    """Tests for attack target types."""

    def test_attacks_on_lane_creeps(self, parsed_replay_data):
        """Should have attacks on lane creeps."""
        creep_attacks = [
            a for a in parsed_replay_data.attacks.events
            if a.target_name and ("creep_goodguys" in a.target_name or "creep_badguys" in a.target_name)
        ]
        assert len(creep_attacks) > 1000

    def test_attacks_on_neutral_creeps(self, parsed_replay_data):
        """Should have attacks on neutral creeps."""
        neutral_attacks = [
            a for a in parsed_replay_data.attacks.events
            if a.target_name and "neutral" in a.target_name.lower()
        ]
        assert len(neutral_attacks) > 100

    def test_attacks_on_heroes(self, parsed_replay_data):
        """Should have attacks on heroes."""
        hero_attacks = [
            a for a in parsed_replay_data.attacks.events
            if a.target_name and "npc_dota_hero" in a.target_name
        ]
        assert len(hero_attacks) > 100

    def test_attacks_on_towers(self, parsed_replay_data):
        """Should have attacks on towers."""
        tower_attacks = [
            a for a in parsed_replay_data.attacks.events
            if a.target_name and "tower" in a.target_name.lower()
        ]
        assert len(tower_attacks) > 50


class TestMatch8594217096Attacks:
    """Tests for attack data in match 8594217096 (OG match)."""

    def test_attacks_data_exists(self, parsed_replay_data_2):
        """Attacks data should be populated."""
        assert parsed_replay_data_2.attacks is not None
        assert len(parsed_replay_data_2.attacks.events) > 10000

    def test_void_spirit_has_single_underscore(self, parsed_replay_data_2):
        """Void Spirit should be void_spirit not void__spirit."""
        vs_attacks = [
            a for a in parsed_replay_data_2.attacks.events
            if "void" in a.attacker_name.lower() and "spirit" in a.attacker_name.lower()
        ]
        if vs_attacks:
            assert "void_spirit" in vs_attacks[0].attacker_name
            assert "void__spirit" not in vs_attacks[0].attacker_name

    def test_juggernaut_has_melee_attacks_match2(self, parsed_replay_data_2):
        """Juggernaut in match 2 should have melee attacks."""
        jug_attacks = [
            a for a in parsed_replay_data_2.attacks.events
            if "juggernaut" in a.attacker_name.lower()
        ]
        melee_jug = [a for a in jug_attacks if a.is_melee]
        assert len(melee_jug) > 100

    def test_pugna_has_ranged_attacks(self, parsed_replay_data_2):
        """Pugna should have ranged attacks."""
        pugna_attacks = [
            a for a in parsed_replay_data_2.attacks.events
            if "pugna" in a.attacker_name.lower()
        ]
        ranged_pugna = [a for a in pugna_attacks if not a.is_melee]
        assert len(ranged_pugna) > 50
