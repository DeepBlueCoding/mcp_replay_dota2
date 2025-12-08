"""Combat-related MCP tools: deaths, combat log, objectives, items, couriers, runes."""

from typing import Optional

from fastmcp import Context

from ..models.combat_log import (
    CombatLogResponse,
    CourierKillsResponse,
    HeroCombatAnalysisResponse,
    HeroDeathsResponse,
    ItemPurchasesResponse,
    ObjectiveKillsResponse,
    RunePickupsResponse,
)


def register_combat_tools(mcp, services):
    """Register combat-related tools with the MCP server."""
    replay_service = services["replay_service"]
    combat_service = services["combat_service"]

    @mcp.tool
    async def get_hero_deaths(match_id: int, ctx: Optional[Context] = None) -> HeroDeathsResponse:
        """
        Get all hero deaths in a Dota 2 match.

        Returns a list of hero death events with:
        - game_time: Seconds since game start
        - game_time_str: Formatted as M:SS
        - killer: Hero or unit that got the kill
        - victim: Hero that died
        - killer_is_hero: Whether the killer was a hero
        - ability: Ability or item that dealt the killing blow (if available)

        Args:
            match_id: The Dota 2 match ID

        Returns:
            HeroDeathsResponse with list of hero death events
        """
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            return combat_service.get_hero_deaths_response(data, match_id)
        except ValueError as e:
            return HeroDeathsResponse(success=False, match_id=match_id, error=str(e))

    @mcp.tool
    async def get_combat_log(
        match_id: int,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        hero_filter: Optional[str] = None,
        significant_only: bool = False,
        ctx: Optional[Context] = None,
    ) -> CombatLogResponse:
        """
        Get combat log events from a Dota 2 match with optional filters.

        Returns combat events including damage, abilities, modifiers (buffs/debuffs), and deaths.

        Each event contains:
        - type: DAMAGE, MODIFIER_ADD, ABILITY, DEATH, ITEM, PURCHASE, BUYBACK, etc.
        - game_time: Seconds since game start
        - game_time_str: Formatted as M:SS
        - attacker: Source of the event (hero name without prefix)
        - attacker_is_hero: Whether attacker is a hero
        - target: Target of the event
        - target_is_hero: Whether target is a hero
        - ability: Ability or item involved (if any)
        - value: Damage amount or other numeric value

        Args:
            match_id: The Dota 2 match ID
            start_time: Filter events after this game time in seconds. **NOTE**: Pre-game purchases
                       (wards, tangos, etc.) happen at NEGATIVE times (~-80s during strategy phase).
                       Use start_time=-90 to include pre-game, or omit entirely to get all events.
                       start_time=0 excludes pre-game purchases. (optional)
            end_time: Filter events before this game time in seconds (optional)
            hero_filter: Only include events involving this hero, e.g. "earthshaker" (optional)
            significant_only: **IMPORTANT**: Controls event filtering. True = only story-telling events
                             (abilities, deaths, items, purchases, buybacks). False = ALL events including
                             every damage tick and modifier application.
                             **WARNING**: False with time ranges >5 minutes produces 50,000+ events and
                             WILL FAIL with "result too large". Always use True for ranges >300 seconds.
                             Default: False (use True for any broad analysis)

        Returns:
            CombatLogResponse with list of combat log events
        """
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            return combat_service.get_combat_log_response(
                data, match_id, start_time, end_time, hero_filter, significant_only
            )
        except ValueError as e:
            return CombatLogResponse(success=False, match_id=match_id, error=str(e))

    @mcp.tool
    async def get_item_purchases(
        match_id: int,
        hero_filter: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> ItemPurchasesResponse:
        """
        Get item purchase timings for heroes in a Dota 2 match.

        Returns a chronological list of item purchases with:
        - game_time: Seconds since game start (can be negative for pre-horn purchases)
        - game_time_str: Formatted as M:SS
        - hero: Hero that purchased the item
        - item: Item name (e.g., "item_bfury", "item_power_treads")

        Use this to answer questions like:
        - "When did Juggernaut finish Battlefury?"
        - "What was Anti-Mage's item progression?"
        - "Who bought the first BKB?"

        Args:
            match_id: The Dota 2 match ID
            hero_filter: Only include purchases by this hero, e.g. "juggernaut" (optional)

        Returns:
            ItemPurchasesResponse with list of item purchase events
        """
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            return combat_service.get_item_purchases_response(data, match_id, hero_filter)
        except ValueError as e:
            return ItemPurchasesResponse(success=False, match_id=match_id, error=str(e))

    @mcp.tool
    async def get_courier_kills(
        match_id: int,
        ctx: Optional[Context] = None,
    ) -> CourierKillsResponse:
        """
        Get all courier kills in a Dota 2 match.

        Returns a list of courier kill events with:
        - game_time: Seconds since game start
        - game_time_str: Formatted as M:SS
        - killer: Hero that killed the courier
        - killer_is_hero: Whether the killer was a hero
        - team: Team whose courier was killed (radiant/dire)

        Args:
            match_id: The Dota 2 match ID

        Returns:
            CourierKillsResponse with list of courier kill events
        """
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            return combat_service.get_courier_kills_response(data, match_id)
        except ValueError as e:
            return CourierKillsResponse(success=False, match_id=match_id, error=str(e))

    @mcp.tool
    async def get_objective_kills(
        match_id: int,
        ctx: Optional[Context] = None,
    ) -> ObjectiveKillsResponse:
        """
        Get all major objective kills in a Dota 2 match.

        Returns kills of:
        - Roshan: game_time, killer, team, kill_number (1st, 2nd, 3rd Roshan)
        - Tormentor: game_time, killer, team, side (which Tormentor was killed)
        - Towers: game_time, tower name, team, tier, lane, killer
        - Barracks: game_time, barracks name, team, lane, type (melee/ranged), killer

        Use this to analyze:
        - When did each team take Roshan?
        - Tower trade patterns and timing
        - High ground pushes and barracks destruction
        - Tormentor control

        Args:
            match_id: The Dota 2 match ID

        Returns:
            ObjectiveKillsResponse with all objective kill events
        """
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            return combat_service.get_objective_kills_response(data, match_id)
        except ValueError as e:
            return ObjectiveKillsResponse(success=False, match_id=match_id, error=str(e))

    @mcp.tool
    async def get_rune_pickups(match_id: int, ctx: Optional[Context] = None) -> RunePickupsResponse:
        """
        Get power rune pickups in a Dota 2 match.

        Returns a list of power rune pickup events with:
        - game_time: Seconds since game start
        - game_time_str: Formatted as M:SS
        - hero: Hero that picked up the rune
        - rune_type: Type of rune (haste, double_damage, arcane, invisibility, regeneration, shield)

        Note: Only power runes are trackable. Bounty, wisdom, and water runes
        don't leave detectable events in the replay data.

        Use this to answer questions like:
        - "Who got the most power runes?"
        - "What runes did the mid player secure?"
        - "When did they get a DD rune before fighting?"

        Args:
            match_id: The Dota 2 match ID

        Returns:
            RunePickupsResponse with list of power rune pickup events
        """
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            return combat_service.get_rune_pickups_response(data, match_id)
        except ValueError as e:
            return RunePickupsResponse(success=False, match_id=match_id, error=str(e))

    fight_service = services["fight_service"]

    @mcp.tool
    async def get_hero_combat_analysis(
        match_id: int,
        hero: str,
        ctx: Optional[Context] = None,
    ) -> HeroCombatAnalysisResponse:
        """
        Analyze a hero's combat involvement across all fights in a match.

        Returns detailed per-fight statistics including:
        - Kills, deaths, and assists in each fight
        - Ability usage with hit rates (e.g., how many Ice Paths landed on heroes)
        - Damage dealt and received
        - Which fights were teamfights vs skirmishes

        Perfect for questions like:
        - "How did Jakiro perform in teamfights?"
        - "How many Ice Paths landed during ganks?"
        - "Which fights did the support participate in?"

        Args:
            match_id: The Dota 2 match ID
            hero: Hero name to analyze (e.g., "jakiro", "earthshaker")

        Returns:
            HeroCombatAnalysisResponse with per-fight and aggregate combat stats
        """
        async def progress_callback(current: int, total: int, message: str) -> None:
            if ctx:
                await ctx.report_progress(current, total)

        try:
            data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
            fight_result = fight_service.get_all_fights(data)
            return combat_service.get_hero_combat_analysis(
                data, match_id, hero, fight_result.fights
            )
        except ValueError as e:
            return HeroCombatAnalysisResponse(
                success=False, match_id=match_id, hero=hero, error=str(e)
            )
