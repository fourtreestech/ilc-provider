"""Faker provider for *ILC* data models.

When imported this module creates a :class:`faker.Faker` instance
and calls ``fake.add_provider(ILCProvider)``.

You can then ``from ilc_provider import fake`` and use the
providers as you would any other Faker provider e.g.::

    from ilc_provider import fake

    player = fake.player()
    match = fake.match()
    league = fake.league()
    // etc.
"""

import contextlib
import datetime
import random
from collections.abc import MutableSequence
from operator import attrgetter
from typing import Any, Literal

from faker import Faker, Generator
from faker.providers import BaseProvider
from ilc_models import (
    BasePlayer,
    Card,
    Event,
    EventTime,
    Goal,
    League,
    Lineup,
    Lineups,
    Match,
    Player,
    Score,
    Substitution,
    TableRow,
    Teams,
)

__version__ = "0.1.3"

fake = Faker()


class SquadPlayer:
    """Member of a squad.

    On initialization the object will be populated
    with a randomly generated :class:`~ilc_models.Player`
    and will be allocated two weighting attributes:

        * ``selection_weight``: How likely this player is to be selected (1-100)
        * ``scorer_weight``: How likely this player is to score a goal (1-100)

    Args:
        shirt_number (int): Player's squad number.
        keeper (bool): True if this player is a goalkeeper. Defaults to False.
        active_date (datetime.date | None): Date on which this player is active - this
            will be used to generate a reasonable date of birth. Defaults to None.
    """

    def __init__(
        self,
        shirt_number: int,
        keeper=False,
        active_date: datetime.date | None = None,
    ):
        """Initialize the squad player."""
        self.shirt_number = shirt_number
        self.keeper = keeper
        self.player = fake.player(active_date=active_date)
        self.selection_weight = random.randint(1, 100)
        self.scorer_weight = 1 if keeper else random.randint(2, 100)

    @property
    def base_player(self) -> BasePlayer:
        """Return a `BasePlayer` object corresponding to this `SquadPlayer`.

        Returns:
            BasePlayer: The `BasePlayer` corresponding to this `SquadPlayer`
        """
        return self.player.base_player

    def __str__(self) -> str:
        """Return the shirt number and name, marking goalkeepers."""
        return (
            f"{self.shirt_number}. {self.player.name}{' (GK)' if self.keeper else ''}"
        )


class Team:
    """Randomly generated team.

    Args:
        active_date (datetime.date | None): Date on which all players in this team's
            squad are active - this will be used to generate reasonable dates of birth.
            Defaults to None.
    """

    def __init__(self, active_date: datetime.date | None = None):
        """Initialize the team with a name, squad and strength."""
        self.name = fake.unique.team_name()
        self.squad = fake.squad(active_date=active_date)
        self.strength = random.randint(0, 5)

    def __str__(self) -> str:  # pragma: no cover
        """Return the team name."""
        return self.name


class ILCProvider(BaseProvider):
    """Faker provider for ILC data models."""

    def __init__(self, generator: Generator) -> None:
        """Initialize the provider.

        Args:
            generator (Generator): Faker generator this provider is attached to.
        """
        super().__init__(generator)
        self.player_ids: set[int] = set()

    def player_id(self) -> int:
        """Return a random player ID.

        Returns:
            int: Random player ID between 1 and 999,999
        """
        while True:
            pid = random.randint(1, 999_999)

            # The `player_ids` set ensures uniqueness
            # within this `ILCProvider` instance
            if pid not in self.player_ids:
                self.player_ids.add(pid)
                return pid

    def base_player(self) -> BasePlayer:
        """Return a randomly generated BasePlayer.

        Returns:
            BasePlayer: BasePlayer with random name and ID
        """
        return BasePlayer(
            player_id=fake.unique.player_id(),
            name=f"{fake.first_name()[0]}. {fake.last_name()}",
        )

    def player(self, active_date: datetime.date | None = None) -> Player:
        """Return a randomly generated Player.

        If ``active_date`` is supplied the player's DOB will be generated
        so that they are between 17 and 35 on ``active_date``,
        otherwise they will be between 17 and 35 on today's date.

        Args:
            active_date (datetime.date | None): Date on which this player is active -
                this will be used to generate a reasonable date of birth. Defaults to
                None.


        Returns:
            Player: Player with randomly generated attributes
        """
        player_id = fake.unique.player_id()
        first_name = fake.first_name_male()
        last_name = fake.last_name_male()
        name = f"{first_name[0]}. {last_name}"
        nationality = fake.country()

        # Get a reasonable DOB
        if active_date is None:
            active_date = datetime.date.today()

        age = random.choices(range(17, 36), weights=[1] * 3 + [2] * 10 + [1] * 6)[0]
        # Any date from the day after their (age + 1)th birthday
        # to their `age`th birthday makes them exactly `age` on active_date
        latest = _years_before(active_date, age)
        earliest = _years_before(active_date, age + 1) + datetime.timedelta(days=1)
        dob = fake.date_between(start_date=earliest, end_date=latest).isoformat()

        return Player(
            player_id=player_id,
            name=name,
            first_name=first_name,
            last_name=last_name,
            dob=dob,
            nationality=nationality,
        )

    def squad(
        self, size=25, keepers=3, active_date: datetime.date | None = None
    ) -> list[SquadPlayer]:
        """Return a randomly generated list of SquadPlayers.

        Args:
            size (int): Number of players to generate. Defaults to 25.
            keepers (int): Number of goalkeepers to include. Defaults to 3.
            active_date (datetime.date | None): Date on which all players in this squad
                are active - this will be used to generate reasonable dates of birth.
                Defaults to None.


        Returns:
            list[SquadPlayer]: List of randomly generated squad players
        """
        # Shirt numbers - prefer 2-11, then 12-19 then 20-39
        shirts = list(range(2, 40))
        shirt_weights = [3] * 10 + [2] * 8 + [1] * 20

        # Generate random shirt numbers for this squad
        shirt_numbers = _unique_choices(shirts, weights=shirt_weights, k=size - 1)

        # One goalkeeper will be shirt 1 - select numbers for any others
        keeper_shirts = [1]
        while len(keeper_shirts) < keepers:
            shirt = random.choice([n for n in shirt_numbers if n > 11])
            keeper_shirts.append(shirt)
            shirt_numbers.remove(shirt)

        # Generate squad
        squad = [
            SquadPlayer(shirt_number=n, keeper=True, active_date=active_date)
            for n in keeper_shirts
        ]
        for n in shirt_numbers:
            squad.append(SquadPlayer(shirt_number=n, active_date=active_date))

        return squad

    def lineup(self, squad: list[SquadPlayer] | None = None) -> Lineup:
        """Return a randomly generated Lineup.

        Creates a lineup with 11 starting players and 7 substitutes.

        If ``squad`` is supplied the players will be chosen from the squad,
        otherwise a new set of players will be randomly generated.

        Args:
            squad (list[SquadPlayer] | None): Squad players to choose from. Defaults to
                None.


        Returns:
            Lineup: Lineup with randomly generated players
        """
        # Get random squad
        if squad is None:
            squad = self.squad(size=18, keepers=2)

        # Decide which goalkeeper will start
        keepers = [p for p in squad if p.keeper]
        keeper_weights = [p.selection_weight for p in keepers]
        keeper1 = random.choices(keepers, weights=keeper_weights)[0]
        keeper2 = next(p for p in keepers if p != keeper1)

        # Get outfield players
        outfield = [p for p in squad if p not in keepers]
        outfield_weights = [p.selection_weight for p in outfield]
        starting = _unique_choices(outfield, weights=outfield_weights, k=10)

        # Get outfield subs
        remaining = [p for p in outfield if p not in starting]
        remaining_weights = [p.selection_weight for p in remaining]
        subs = _unique_choices(remaining, weights=remaining_weights, k=6)

        # Make lineup
        lineup = Lineup(
            starting=[(keeper1.shirt_number, keeper1.base_player)]
            + [(p.shirt_number, p.base_player) for p in starting],
            subs=[(keeper2.shirt_number, keeper2.base_player)]
            + [(p.shirt_number, p.base_player) for p in subs],
        )

        return lineup

    def lineups(
        self,
        home_squad: list[SquadPlayer] | None = None,
        away_squad: list[SquadPlayer] | None = None,
    ) -> Lineups:
        """Return two randomly generated lineups.

        If ``home_squad`` or ``away_squad`` is supplied the players will be chosen from the squads,
        otherwise new sets of players will be randomly generated.

        Args:
            home_squad (list[SquadPlayer] | None): Squad players for the home team.
                Defaults to None.
            away_squad (list[SquadPlayer] | None): Squad players for the away team.
                Defaults to None.


        Returns:
            Lineups: Lineups with randomly generated players
        """
        return Lineups(home=self.lineup(home_squad), away=self.lineup(away_squad))

    def team_suffix(self) -> str:
        """Return a team suffix (United, City, etc.).

        Returns:
            str: Randomly selected suffix
        """
        suffixes = (
            "Albion",
            "Argyle",
            "Athletic",
            "City",
            "County",
            "Dons",
            "FC",
            "Forest",
            "Hotspur",
            "North End",
            "Orient",
            "Palace",
            "Rangers",
            "Rovers",
            "Swifts",
            "Town",
            "United",
            "Wanderers",
            "Wednesday",
            "",
        )
        return random.choice(suffixes)

    def team_name(self) -> str:
        """Return a randomly generated team name.

        Returns:
            str: Team name
        """
        return f"{fake.city()} {fake.team_suffix()}".rstrip()

    def team(self, active_date: datetime.date | None = None) -> Team:
        """Return a randomly generated team.

        Args:
            active_date (datetime.date | None): Date on which all players in this team's
                squad are active - this will be used to generate reasonable dates of
                birth. Defaults to None.


        Returns:
            Team: Randomly generated team, populated with a squad of players
        """
        return Team(active_date=active_date)

    def match_id(self) -> int:
        """Return a random match ID.

        Returns:
            int: Random match ID between 1 and 999,999
        """
        return random.randint(1, 999_999)

    def match(
        self,
        kickoff: datetime.datetime | None = None,
        round: str | None = None,
        home: Team | None = None,
        away: Team | None = None,
        status: str | None = None,
    ) -> Match:
        """Return a randomly generated match.

        Takes a number of optional parameters which if supplied
        will be added to the match. Any parameters not
        supplied will be randomly generated.

        Args:
            kickoff (datetime.datetime | None): Kickoff time. Defaults to None.
            round (str | None): Round this match is part of. Defaults to None.
            home (Team | None): Home team. Defaults to None.
            away (Team | None): Away team. Defaults to None.
            status (str | None): Match status. Defaults to None.


        Returns:
            Match: Randomly generated match
        """
        # Kickoff time if not provided
        if kickoff is None:
            date = fake.past_date(start_date="-1y")
            kickoff = datetime.datetime(
                date.year,
                date.month,
                date.day,
                hour=15,
                tzinfo=datetime.timezone(datetime.timedelta()),
            )

        # Teams if not provided
        if home is None:
            home = fake.team()
        if away is None:
            away = fake.team()

        # Help out the type checker
        assert home is not None
        assert away is not None

        # Create match object
        match = Match(
            match_id=fake.unique.match_id(),
            kickoff=kickoff.isoformat(),
            round=round or f"Round {random.randint(1, 38)}",
            teams=Teams(home=home.name, away=away.name),
            status=status or "FT",
        )

        if match.played:
            # Score - start with the strength difference
            # between the two teams
            strength_delta = home.strength - away.strength

            # Weight possible score differences depending on the strength difference
            counts = [12 - abs(n - strength_delta) for n in range(-5, 6)]

            # Select from the weighted score differences
            score_delta = random.sample(range(-5, 6), 1, counts=counts)[0]

            # Convert to an actual score
            # 0 or -1 is a draw, other negative numbers are an away win,
            # positive numbers are a home win
            low_score = random.randint(0, 2)
            if score_delta < 1:
                home_score = low_score
                away_score = (
                    home_score
                    if score_delta in (0, -1)
                    else home_score + abs(score_delta + 1)
                )
            else:
                away_score = low_score
                home_score = away_score + score_delta
            match.score = Score(home=home_score, away=away_score)

            # Lineups
            match.lineups = self.lineups(home_squad=home.squad, away_squad=away.squad)

            # Substitutions
            for team, lineup in zip(
                (home, away), (match.lineups.home, match.lineups.away), strict=True
            ):
                # Exclude goalkeepers from substitutions
                keepers = [p.base_player for p in team.squad if p.keeper]
                possible_exits = [p[1] for p in lineup.starting if p[1] not in keepers]
                possible_entries = [p[1] for p in lineup.subs if p[1] not in keepers]

                total_subs = random.randint(1, min(5, len(possible_entries)))
                subs: list[Substitution] = []
                windows_used = 0

                while (
                    len(subs) < total_subs
                    and len(possible_entries) > 0
                    and len(possible_exits) > 0
                ):
                    # Get sub window
                    window_subs = self.sub_window(
                        team=team.name,
                        sub_count=total_subs - len(subs) if windows_used == 2 else 0,
                        time=None,
                        possible_exits=possible_exits,
                        possible_entries=possible_entries,
                    )

                    # Remove players used
                    for sub in window_subs:
                        possible_entries.remove(sub.player_on)
                        possible_exits.remove(sub.player_off)

                    subs += window_subs
                    windows_used += 1

                match.substitutions.extend(subs[:total_subs])

            # Cards
            for team, lineup in zip(
                (home, away), (match.lineups.home, match.lineups.away), strict=True
            ):
                # 0-4 cards per team per match
                total_cards = random.choice(range(5))

                # Card times, sorted in chronological order
                times = sorted([self.event_time() for _ in range(total_cards)])

                cards: list[Card] = []
                for time in times:
                    # Check for players with a red card
                    sent_off = []
                    for card in cards:
                        if card.color == "R":
                            sent_off.append(card.player)

                    # Get players currently on the pitch
                    players = players_on(
                        team.name,
                        [p[1] for p in lineup.starting],
                        match.events(),
                        time,
                    )

                    # Make card
                    while True:
                        new_card = self.card(team.name, time, players)
                        if new_card.player not in sent_off:
                            break
                    new_cards = [new_card]

                    # Check if this player has already received a yellow card
                    for existing_card in cards:
                        if (
                            existing_card.player == new_card.player
                            and new_card.color == "Y"
                        ):
                            # Second yellow - add the yellow and then a red card
                            new_cards.append(
                                Card(
                                    team=new_card.team,
                                    time=new_card.time,
                                    color="R",
                                    player=new_card.player,
                                )
                            )

                    cards.extend(new_cards)

                    # Red card - check the player doesn't get subbed off later in the match
                    last_card = cards[-1]
                    if last_card.color == "R":
                        # Check for the player being substituted off
                        sub_index = -1
                        for i, sub in enumerate(match.substitutions):
                            if last_card.player == sub.player_off:
                                sub_index = i
                                break
                        if sub_index != -1:
                            del match.substitutions[sub_index]

                match.cards.extend(cards)

            # Goals
            for (
                scoring_team,
                other_team,
                scoring_lineup,
                other_lineup,
                goal_count,
            ) in zip(
                (home, away),
                (away, home),
                (match.lineups.home, match.lineups.away),
                (match.lineups.away, match.lineups.home),
                (match.score.home, match.score.away),
                strict=True,
            ):
                for _ in range(goal_count):
                    time = self.event_time()
                    scoring_team_players = players_on(
                        scoring_team.name,
                        [p[1] for p in scoring_lineup.starting],
                        match.events(),
                        time,
                    )
                    other_team_players = players_on(
                        other_team.name,
                        [p[1] for p in other_lineup.starting],
                        match.events(),
                        time,
                    )
                    match.goals.append(
                        self.goal(
                            team=scoring_team,
                            time=time,
                            players=(scoring_team_players, other_team_players),
                        )
                    )

        return match

    def sub_window(
        self,
        team: str | None = None,
        sub_count: int = 0,
        time: EventTime | None = None,
        possible_exits: list[BasePlayer] | None = None,
        possible_entries: list[BasePlayer] | None = None,
    ) -> list[Substitution]:
        """Return a randomly generated list of substitutions made within a single window.

        Any parameters not supplied will be randomly generated.

        Args:
            team (str | None): Name of the team making this substitution. Defaults to
                None.
            sub_count (int): Number of substitutions to be made in this window. Defaults
                to 0.
            time (EventTime | None): Time of the substitutions. Defaults to None.
            possible_exits (list[BasePlayer] | None): Players who can come off the
                field. Defaults to None.
            possible_entries (list[BasePlayer] | None): Players who can come on the
                field. Defaults to None.


        Returns:
            list[Substitution]: Randomly generated substitutions
        """
        if team is None:
            team = self.team_name()

        if sub_count == 0:
            max_subs = len(possible_exits) if possible_exits else 3
            sub_count = random.randint(1, max_subs)

        if time is None:
            # Subs are much more likely in the second half
            time = self.event_time(first_half_weighting=10)

        # Players to come on/off
        exits = (
            possible_exits[:]
            if possible_exits
            else [self.base_player() for _ in range(sub_count)]
        )
        entries = (
            possible_entries[:]
            if possible_entries
            else [self.base_player() for _ in range(sub_count)]
        )

        # Generate subs list
        subs: list[Substitution] = []
        while len(subs) < sub_count:
            sub = self.substitution(team, time, exits, entries)
            exits.remove(sub.player_off)
            entries.remove(sub.player_on)
            subs.append(sub)
            if len(entries) == 0 or len(exits) == 0:
                break

        return subs

    def substitution(
        self,
        team: str | None = None,
        time: EventTime | None = None,
        possible_exits: list[BasePlayer] | None = None,
        possible_entries: list[BasePlayer] | None = None,
    ) -> Substitution:
        """Return a randomly generated substitution.

        Any parameters not supplied will be randomly generated.

        Args:
            team (str | None): Name of the team making this substitution. Defaults to
                None.
            time (EventTime | None): Time of the substitution. Defaults to None.
            possible_exits (list[BasePlayer] | None): Players who can come off the
                field. Defaults to None.
            possible_entries (list[BasePlayer] | None): Players who can come on the
                field. Defaults to None.


        Returns:
            Substitution: Randomly generated substitution
        """
        if team is None:
            team = self.team_name()

        if time is None:
            # Subs are much more likely in the second half
            time = self.event_time(first_half_weighting=10)

        if not possible_exits:  # pragma: no cover
            possible_exits = [self.base_player()]

        if not possible_entries:  # pragma: no cover
            possible_entries = [self.base_player()]

        return Substitution(
            team=team,
            time=time,
            player_on=random.choice(possible_entries),
            player_off=random.choice(possible_exits),
        )

    def card(
        self,
        team: str | None = None,
        time: EventTime | None = None,
        players: list[BasePlayer] | None = None,
    ) -> Card:
        """Return a randomly generated red or yellow card.

        Any parameters not supplied will be randomly generated.

        Args:
            team (str | None): Name of the team receiving this card. Defaults to None.
            time (EventTime | None): Time of the card. Defaults to None.
            players (list[BasePlayer] | None): Players who can receive the card.
                Defaults to None.


        Returns:
            Card: Randomly generated card event
        """
        if team is None:  # pragma: no cover
            team = self.team_name()

        if time is None:  # pragma: no cover
            time = self.event_time()

        if not players:  # pragma: no cover
            players = [self.base_player()]

        # 1 in 30 cards given is a straight red
        color: Literal["Y", "R"] = "R" if random.randint(1, 30) == 30 else "Y"
        player = random.choice(players)

        return Card(team=team, time=time, color=color, player=player)

    def goal(
        self,
        team: Team | None = None,
        time: EventTime | None = None,
        goal_type: Literal["N", "O", "P"] | None = None,
        players: tuple[list[BasePlayer], list[BasePlayer]] | None = None,
    ) -> Goal:
        """Return a randomly generated goal.

        Any parameters not supplied will be randomly generated.

        Args:
            team (Team | None): Team scoring this goal. Defaults to None.
            time (EventTime | None): Time of the goal. Defaults to None.
            goal_type (str | None): One of 'N' (normal goal), 'O' (own goal), 'P'
                (penalty). Defaults to None.
            players (tuple[list[BasePlayer], list[BasePlayer]] | None): Players who can
                score the goal as a two-item tuple, the scoring team's players are the
                first item and the opposing team's players (for own goals) are the
                second item. Defaults to None.


        Returns:
            Goal: Randomly generated goal event
        """
        if team is None:  # pragma: no cover
            team = self.team()

        if time is None:
            time = self.event_time()

        # 1 in 10 goals is a penalty
        # 1 in 30 goals is an own goal
        if goal_type is None:
            if random.randint(1, 10) == 10:
                goal_type = "P"
            elif random.randint(1, 30) == 30:
                goal_type = "O"
            else:
                goal_type = "N"

        # Own goal
        if goal_type == "O":
            if players is None:  # pragma: no cover
                scorer = self.base_player()
            else:
                scorer = random.choice(players[1])

        # Penalty or normal goal
        else:
            if players is None:
                lineup = self.lineup(team.squad)
                players = ([p[1] for p in lineup.starting], [])
            # Select scorer
            potential_scorers = [p for p in team.squad if p.base_player in players[0]]
            potential_scorers.sort(key=attrgetter("scorer_weight"), reverse=True)

            # Penalty is scored by the top weighted scorer
            if goal_type == "P":
                scorer = potential_scorers[0].base_player
            else:
                scorer = random.choices(
                    [p.base_player for p in potential_scorers],
                    [p.scorer_weight for p in potential_scorers],
                    k=1,
                )[0]

        return Goal(team=team.name, time=time, goal_type=goal_type, scorer=scorer)

    def event_time(self, first_half_weighting=50) -> EventTime:
        """Return a randomly generated event time.

        The ``first_half_weighting`` parameter controls how likely it is
        that the time will be in the first half. A value of 50 means
        either half will have equal probability; higher values increase
        the likelihood of a first half time.

        Args:
            first_half_weighting (int): Weight / 100 to give to a time in the first
                half.


        Returns:
            EventTime: Randomly generated event time
        """
        half = 0 if random.randint(1, 100) <= first_half_weighting else 1
        time = random.randint(1, 50)
        minutes = min(time, 45) + 45 * half
        plus = max(time - 45, 0)
        return EventTime(minutes=minutes, plus=plus)

    def kickoff(
        self, anchor: datetime.date | None = None, midweek: bool = False
    ) -> datetime.datetime:
        """Return a randomly generated kickoff time.

        If ``anchor`` is provided the kickoff will be on that day at 15:00 or 17:30,
        the following day at 15:00, or at 19:45 on d-1.
        This simulates a gameweek being played across a Friday to Sunday,
        where ``anchor`` is the Saturday.

        If ``midweek`` is true the gameweek is played across a Tuesday and Wednesday
        instead, where ``anchor`` is the Tuesday: the kickoff will be at 19:45 on
        either day.

        If ``anchor`` is not provided the kickoff will be a random Saturday at 3pm.

        Args:
            anchor (datetime.date | None): Saturday to anchor this gameweek, or
                Tuesday if ``midweek`` is true. Defaults to None.
            midweek (bool): Whether the gameweek is played midweek. Only used if
                ``anchor`` is provided. Defaults to False.


        Returns:
            datetime.datetime: Randomly generated kickoff date and time
        """
        # No anchor supplied - generate a random Saturday 3pm kickoff time
        if anchor is None:
            anchor = fake.date_this_century(after_today=False)
            anchor += datetime.timedelta(days=5 - anchor.weekday())
            return datetime.datetime.combine(
                anchor,
                datetime.time(hour=15),
                tzinfo=datetime.timezone(datetime.timedelta()),
            )

        # Anchor supplied - possible timedeltas
        if midweek:
            deltas = (
                datetime.timedelta(hours=19, minutes=45),  # Tue 19:45
                datetime.timedelta(days=1, hours=19, minutes=45),  # Wed 19:45
            )
            # Tue is most likely
            weights = (2, 1)
        else:
            deltas = (
                datetime.timedelta(hours=-4, minutes=-15),  # Fri 19:45
                datetime.timedelta(hours=15),  # Sat 15:00
                datetime.timedelta(hours=17, minutes=30),  # Sat 17:30
                datetime.timedelta(days=1, hours=15),  # Sun 15:00
            )
            # Sat 3pm is most likely
            weights = (2, 4, 2, 1)
        delta = random.choices(deltas, weights, k=1)[0]

        # Make datetime object and return
        dt = datetime.datetime.combine(
            anchor, datetime.time(), tzinfo=datetime.timezone(datetime.timedelta())
        )
        return dt + delta

    def table_row(self, matches: int = 0, team: Team | None = None) -> TableRow:
        """Return a randomly generated league table row.

        Any parameters not supplied will be randomly generated.

        Args:
            matches (int): Matches played. Defaults to 0.
            team (Team | None): Team. Defaults to None.


        Returns:
            TableRow: Randomly generated row from a league table
        """

        def weighted_results(matches: int, strength: int) -> int:
            """Get a weighted number of match results based on a team's strength.

            Higher strength will tend towards a higher return value.

            Args:
                matches (int): Number of matches to play.
                strength (int): Strength factor (0-5).


            Returns:
                int: Weighted random number of matches
            """
            matches_per_step = max((matches + 1) // 5, 1)
            steps = [min(n // matches_per_step, 5) for n in range(matches + 1)]
            weights = [6 - abs(strength - step) for step in steps]
            return random.sample(range(matches + 1), k=1, counts=weights)[0]

        if team is None:
            team = self.team()

        if matches == 0:  # pragma: no cover
            matches = random.randint(1, 38)

        # Base win/draw rate on team strength
        won = weighted_results(matches, team.strength)
        drawn = weighted_results(matches - won, team.strength)
        lost = matches - (won + drawn)

        # Goals for and against
        scored = (
            won * random.randint(10, 30)
            + drawn * random.randint(0, 20)
            + lost * random.randint(0, 10)
        ) // 10
        conceded = (
            won * random.randint(0, 10)
            + drawn * random.randint(0, 20)
            + lost * random.randint(10, 30)
        ) // 10

        # Form
        form = random.sample("WDL", min(matches, 5), counts=[won, drawn, lost])

        return TableRow(
            team=team.name,
            won=won,
            drawn=drawn,
            lost=lost,
            scored=scored,
            conceded=conceded,
            form="".join(form),
        )

    def league_id(self) -> int:
        """Return a random league ID.

        Returns:
            int: Random match ID between 1 and 999
        """
        return random.randint(1, 999)

    def league_name(self) -> str:
        """Return a randomly selected league name.

        Returns:
            str: Random league name
        """
        names = (
            "Premiership",
            "Premier League",
            "Championship",
            "Division 1",
            "Division 2",
            "League 1",
            "League 2",
        )
        return random.choice(names)

    def league(
        self,
        team_count: int = 0,
        matches: bool = True,
        games_per_opponent: int = 0,
        split_mode: Literal["auto", "none", "fixed"] = "auto",
        games_before_split: int = 3,
    ) -> League:
        """Return a randomly generated league.

        If ``matches`` is False no matches will be added to the league.

        If ``games_per_opponent`` is not provided it will default to
        2 for leagues with more than 12 teams, or 4 otherwise.

        If ``split_mode`` is not provided it will default to `auto` and
        a split will occur in leagues with 3 or more games per opponent.

        Any other parameters not supplied will be randomly generated.

        Args:
            team_count (int): Number of teams in this league. Defaults to 0.
            matches (bool): Whether matches should be added to this league. Defaults to
                True.
            games_per_opponent (int): Number of games to play against each other team
                (including post-split games). Defaults to 0.
            split_mode (str): One of 'none' (no split), 'auto' (auto-generated split
                point) or 'fixed' (use split point provided). Defaults to 'auto'.
            games_before_split (int): Number of matches to play against each opponent
                before the league splits in 'fixed' split mode, ignored if `split_mode`
                is 'none' or 'auto'. Defaults to 3.


        Returns:
            League: Randomly generated league

        Raises:
            ValueError: If ``split_mode`` is 'fixed' and ``games_before_split`` is not
                less than ``games_per_opponent``.
        """
        # Basic info
        league_id = fake.unique.league_id()
        name = self.league_name()
        year = int(fake.year())
        current = random.randint(0, 1) == 0
        coverage = {
            "events": True,
            "lineups": True,
            "players": True,
        }

        # Start and end dates
        start_date = fake.date_between_dates(
            date_start=datetime.date(year, 1, 2), date_end=datetime.date(year, 12, 25)
        )

        # Make sure we start on a Saturday, without leaving the year
        start_date += datetime.timedelta(days=(5 - start_date.weekday()) % 7)
        end_date = start_date + datetime.timedelta(
            days=7 * 38
        )  # Will adjust this later based on actual game dates

        # Convert to ISO strings
        start = start_date.isoformat()[:10]
        end = end_date.isoformat()[:10]

        # Create league object
        league = League(
            league_id=league_id,
            name=name,
            year=year,
            start=start,
            end=end,
            current=current,
            coverage=coverage,
        )

        # Generate teams - select an even number of teams between 8 and 24
        if team_count == 0:
            team_count = random.randint(4, 12) * 2
        if team_count % 2:  # pragma: no cover
            team_count -= 1

        teams = [self.team(active_date=start_date) for _ in range(team_count)]
        league.teams = sorted([team.name for team in teams])

        # Get players
        league.players = {
            str(p.player.player_id): p.player for team in teams for p in team.squad
        }

        if not matches:
            return league

        # Determine matches to play
        if games_per_opponent == 0:  # pragma: no cover
            games_per_opponent = 4 if team_count <= 12 else 2

        # Determine split point
        if split_mode == "none":
            games_before_split = 0
        elif split_mode == "auto":
            if games_per_opponent < 3:
                games_before_split = 0
            elif games_per_opponent < 5:
                games_before_split = games_per_opponent - 1
            else:
                games_before_split = games_per_opponent - 2
        elif games_before_split >= games_per_opponent:
            raise ValueError(
                "games_before_split must be less than games_per_opponent in 'fixed' "
                "split mode"
            )
        league.split = games_before_split * (team_count - 1)

        # Generate a set of match days
        schedule = match_schedule(teams)
        rounds = schedule[:]

        # Continue up to the split if there is one
        full_rounds = games_before_split or games_per_opponent
        for _ in range(1, full_rounds):
            schedule = invert_schedule(schedule)
            rounds += schedule

        # Now generate matches and add to the league
        kickoff = datetime.date(
            start_date.year,
            start_date.month,
            start_date.day,
        )
        for n, r in enumerate(rounds, start=1):
            round_name = f"Round {n}"
            round_matches = [
                self.match(
                    kickoff=self.kickoff(kickoff, midweek=kickoff.weekday() == 1),
                    round=round_name,
                    home=m[0],
                    away=m[1],
                )
                for m in r
            ]
            league.rounds[round_name] = round_matches

            # Tuesday night games every fourth week
            match n % 5:
                case 0 | 1 | 2:
                    kickoff += datetime.timedelta(days=7)
                case 3:
                    kickoff += datetime.timedelta(days=3)
                case 4:
                    kickoff += datetime.timedelta(days=4)

        # Generate post-split matches
        games_after_split = games_per_opponent - (
            games_before_split or games_per_opponent
        )
        if games_after_split:
            # Get top and bottom sections
            table = league.table()
            team_names = [row[0] for row in table]
            split_names = [
                team_names[: len(team_names) // 2],
                team_names[len(team_names) // 2 :],
            ]
            split_teams = []
            for section in split_names:
                section_teams = []
                for team_name in section:
                    for team in teams:
                        if team.name == team_name:
                            section_teams.append(team)
                            break
                split_teams.append(section_teams)

            # Generate match days
            split_schedule = [match_schedule(t) for t in split_teams]

            # Adjust home and away if pre- and post-split is an
            # odd number of games
            if games_before_split % 2 and games_after_split % 2:
                for schedule in split_schedule:
                    for round in schedule:
                        for i in range(len(round)):
                            home, away = round[i]
                            home_count = 0
                            away_count = 0
                            h2h = league.head_to_head((home.name, away.name))
                            for match in h2h:
                                if match.teams.home == home.name:
                                    home_count += 1
                                else:
                                    away_count += 1
                            if home_count > away_count:
                                round[i] = (away, home)

            split_rounds = [s[:] for s in split_schedule]
            for _ in range(1, games_after_split):
                split_schedule = [invert_schedule(s) for s in split_schedule]
                for rounds, schedule in zip(split_rounds, split_schedule, strict=True):
                    rounds += schedule

            # Generate matches
            # Resume on the Saturday after the last pre-split round
            split_kickoff = kickoff + datetime.timedelta(
                days=(5 - kickoff.weekday()) % 7 + 7
            )
            for section_number, s_rounds in enumerate(split_rounds, start=1):
                kickoff = split_kickoff
                for n, s_round in enumerate(s_rounds, start=1):
                    round_name = f"Section {section_number} Round {n}"
                    league.rounds[round_name] = [
                        self.match(
                            kickoff=self.kickoff(kickoff),
                            round=round_name,
                            home=m[0],
                            away=m[1],
                        )
                        for m in s_round
                    ]
                    kickoff += datetime.timedelta(days=7)

        # Adjust league start and end dates to reflect first and final matches
        matches_played = league.matches()
        league.start = matches_played[0].date.isoformat()
        league.end = matches_played[-1].date.isoformat()

        return league


def match_schedule(teams: list[Team]) -> list[list[tuple[Team, Team]]]:
    """Develop a match schedule with each team playing all others once.

    Returns a list of matchdays, each containing a list of fixtures
    in the form of (home, away) tuples.

    Args:
        teams (list[Team]): Teams to schedule.


    Returns:
        list[list[tuple[Team, Team]]]: Schedule of matches
    """
    team_count = len(teams)

    # Need to have an even number of teams to create the schedule
    if team_count % 2:
        team_count += 1

    rounds = []
    for round in range(team_count - 1):
        matches = []
        for match in range(team_count // 2):
            home = (round + match) % (team_count - 1)
            away = (team_count - 1 - match + round) % (team_count - 1)
            if match == 0:
                if round % 2:
                    away = team_count - 1
                else:
                    away = home
                    home = team_count - 1

            # Skip non-existent team in odd-numbered scenario
            with contextlib.suppress(IndexError):
                matches.append((teams[home], teams[away]))

        rounds.append(matches)

    return rounds


def invert_schedule(
    schedule: list[list[tuple[Team, Team]]],
) -> list[list[tuple[Team, Team]]]:
    """Invert all fixtures in the schedule so home becomes away and vice versa.

    Also shuffles the match days so they reoccur in a randomized order.

    Args:
        schedule (list[list[tuple[Team, Team]]]): Schedule to invert.


    Returns:
        list[list[tuple[Team, Team]]]: Inverted schedule
    """
    rounds = []
    for round in schedule:
        rounds.append([(away, home) for (home, away) in round])
    random.shuffle(rounds)
    return rounds


def players_on(
    team: str, starting: list[BasePlayer], events: list[Event], time: EventTime
) -> list[BasePlayer]:
    """Return the list of players on the pitch at a given time.

    Args:
        team (str): Team name.
        starting (list[BasePlayer]): Starting XI.
        events (list[Event]): Match events.
        time (EventTime): Time to check.

    Returns:
        list[BasePlayer]: Players on the pitch at ``time``.
    """
    # Starting lineup
    players = starting[:]

    # Adjust according to events
    for event in events:
        # Check if event has occurred at the given time
        if event.team == team and event.time < time:
            match event:
                # Adjust for subs
                case Substitution(player_on=player_on, player_off=player_off):
                    players.remove(player_off)
                    players.append(player_on)

                # Remove any players sent off
                case Card(player=player, color=color):
                    if color == "R":
                        players.remove(player)

    return players


def _years_before(date: datetime.date, years: int) -> datetime.date:
    """Return the date `years` years before `date`.

    29 February maps to 28 February when the earlier year is not a leap year.

    Args:
        date (datetime.date): Date to count back from.
        years (int): Number of years to go back.


    Returns:
        datetime.date: The same day and month `years` years earlier
    """
    try:
        return date.replace(year=date.year - years)
    except ValueError:
        return date.replace(year=date.year - years, day=28)


def _unique_choices(
    population: MutableSequence[Any], weights: list[int] | None = None, k=1
) -> list[Any]:
    """Return a `k` sized list of elements chosen from the `population` without replacement.

    Args:
        population (MutableSequence[Any]): Population to select elements from.
        weights (list[int] | None): If specified, selections are made
            according to the relative weights. Defaults to None.
        k (int): Number of selections to return. Defaults to 1.


    Returns:
        list[Any]: Selected elements
    """
    _population = population[:]
    _weights = weights[:] if weights is not None else None

    choices: list[Any] = []
    while len(choices) < k:
        choice = random.choices(_population, weights=_weights)[0]
        choices.append(choice)
        i = _population.index(choice)
        del _population[i]
        if _weights:
            del _weights[i]

    return choices


fake.add_provider(ILCProvider)
