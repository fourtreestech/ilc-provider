"""Faker provider for *ILC* data models.

When imported this module creates a :class:`faker.Faker` instance
and calls ``fake.add_provider(ILCProvider)``.

You can then ``from ilc_models import fake`` and use the
providers as you would any other Faker provider e.g.::

    from ilc_models import fake

    player = fake.player()
    match = fake.match()
    league = fake.league()
    // etc.
"""

import datetime
import random
from collections.abc import MutableSequence
from operator import attrgetter
from typing import Optional, Any, Literal

from faker import Faker
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

__version__ = "0.1.1"

fake = Faker()


class SquadPlayer:
    """Member of a squad.

    On initialization the object will be populated
    with a randomly generated :class:`~ilc_models.Player`
    and will be allocated two weighting attributes:

        * ``selection_weight``: How likely this player is to be selected (1-100)
        * ``scorer_weight``: How likely this player is to score a goal (1-100)

    :param shirt_number: Player's squad number
    :type shirt_number: int
    :param keeper: True if this player is a goalkeeper (default=False)
    :type keeper: bool
    :param active_date: Date on which this player is active - this will
                        be used to generate a reasonable date of birth (default=None)
    :type active_date: :class:`datetime.date`
    """

    def __init__(
        self,
        shirt_number: int,
        keeper=False,
        active_date: Optional[datetime.date] = None,
    ):
        self.shirt_number = shirt_number
        self.keeper = keeper
        self.player = fake.player(active_date=active_date)
        self.selection_weight = random.randint(1, 100)
        self.scorer_weight = 1 if keeper else random.randint(2, 100)

    @property
    def base_player(self) -> BasePlayer:
        """Return a `BasePlayer` object corresponding to this `SquadPlayer`.

        :returns: The `BasePlayer` corresponding to this `SquadPlayer`
        :rtype: :class:`ilc_models.BasePlayer`
        """
        return self.player.base_player

    def __str__(self) -> str:
        return (
            f"{self.shirt_number}. {self.player.name}{' (GK)' if self.keeper else ''}"
        )


class Team:
    """Randomly generated team.

    :param active_date: Date on which all players in this team's squad are active - this will
                        be used to generate reasonable dates of birth (default=None)
    :type active_date: :class:`datetime.date`
    """

    def __init__(self, active_date: Optional[datetime.date] = None):
        self.name = fake.unique.team_name()
        self.squad = fake.squad(active_date=active_date)
        self.strength = random.randint(0, 5)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class ILCProvider(BaseProvider):
    """Faker provider for ILC data models"""

    player_ids: set[int] = set()

    def player_id(self) -> int:
        """Returns a random player ID.

        :returns: Random player ID between 1 and 999,999
        :rtype: int
        """
        while True:
            pid = random.randint(1, 999_999)

            # The `player_ids` set ensures uniqueness
            # within this `ILCProvider` instance
            if pid not in self.player_ids:
                self.player_ids.add(pid)
                return pid

    def base_player(self) -> BasePlayer:
        """Returns a randomly generated BasePlayer.

        :returns: BasePlayer with random name and ID
        :rtype: :class:`ilc_models.BasePlayer`
        """
        return BasePlayer(
            player_id=fake.unique.player_id(),
            name=f"{fake.first_name()[0]}. {fake.last_name()}",
        )

    def player(self, active_date: Optional[datetime.date] = None) -> Player:
        """Returns a randomly generated Player.

        If ``active_date`` is supplied the player's DOB will be generated
        so that they are between 17 and 35 on ``active_date``,
        otherwise they will be between 17 and 35 on today's date.

        :param active_date: Date on which this player is active - this will
                            be used to generate a reasonable date of birth (default=None)
        :type active_date: :class:`datetime.date`
        :returns: Player with randomly generated attributes
        :rtype: :class:`ilc_models.Player`
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
        year = active_date.year - age
        dob = fake.date_between(
            start_date=datetime.date(year, 1, 1), end_date=datetime.date(year, 12, 31)
        ).isoformat()

        return Player(
            player_id=player_id,
            name=name,
            first_name=first_name,
            last_name=last_name,
            dob=dob,
            nationality=nationality,
        )

    def squad(
        self, size=25, keepers=3, active_date: Optional[datetime.date] = None
    ) -> list[SquadPlayer]:
        """Returns a randomly generated list of SquadPlayers.

        :param size: Number of players to generate (default=25)
        :type size: int
        :param keepers: Number of goalkeepers to include (default=3)
        :type keepers: int
        :param active_date: Date on which all players in this squad are active - this will
                            be used to generate reasonable dates of birth (default=None)
        :type active_date: :class:`datetime.date`
        :returns: List of randomly generated squad players
        :rtype: list[:class:`SquadPlayer`]
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

    def lineup(self, squad: Optional[list[SquadPlayer]] = None) -> Lineup:
        """Returns a randomly generated Lineup.

        Creates a lineup with 11 starting players and 7 substitutes.

        If ``squad`` is supplied the players will be chosen from the squad,
        otherwise a new set of players will be randomly generated.

        :param squad: Squad players to choose from (default=None)
        :type squad: list[:class:`SquadPlayer`]
        :returns: Lineup with randomly generated players
        :rtype: :class:`ilc_models.Lineup`
        """
        # Get random squad
        if squad is None:
            squad = self.squad(size=18, keepers=2)

        # Decide which goalkeeper will start
        keepers = [p for p in squad if p.keeper]
        keeper_weights = [p.selection_weight for p in keepers]
        keeper1 = random.choices(keepers, weights=keeper_weights)[0]
        keeper2 = [p for p in keepers if p != keeper1][0]

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
        home_squad: Optional[list[SquadPlayer]] = None,
        away_squad: Optional[list[SquadPlayer]] = None,
    ) -> Lineups:
        """Returns two randomly generated lineups.

        If ``home_squad`` or ``away_squad`` is supplied the players will be chosen from the squads,
        otherwise new sets of players will be randomly generated.

        :param home_squad: Squad players for the home team (default=None)
        :type home_squad: list[:class:`SquadPlayer`]
        :param away_squad: Squad players for the home team (default=None)
        :type away_squad: list[:class:`SquadPlayer`]
        :returns: Lineups with randomly generated players
        :rtype: :class:`ilc_models.Lineups`
        """
        return Lineups(home=self.lineup(home_squad), away=self.lineup(away_squad))

    def team_suffix(self) -> str:
        """Returns a team suffix (United, City, etc.).

        :returns: Randomly selected suffix
        :rtype: str
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
        """Returns a randomly generated team name.

        :returns: Team name
        :rtype: str
        """
        return " ".join((fake.city(), fake.team_suffix())).rstrip()

    def team(self, active_date: Optional[datetime.date] = None) -> Team:
        """Returns a randomly generated team.

        :param active_date: Date on which all players in this team's squad are active - this will
                            be used to generate reasonable dates of birth (default=None)
        :type active_date: :class:`datetime.date`
        :returns: Randomly generated team, populated with a squad of players
        :rtype: :class:`Team`
        """
        return Team(active_date=active_date)

    def match_id(self) -> int:
        """Returns a random match ID.

        :returns: Random match ID between 1 and 999,999
        :rtype: int
        """
        return random.randint(1, 999_999)

    def match(
        self,
        kickoff: Optional[datetime.datetime] = None,
        round: Optional[str] = None,
        home: Optional[Team] = None,
        away: Optional[Team] = None,
        status: Optional[str] = None,
    ) -> Match:
        """Returns a randomly generated match.

        Takes a number of optional parameters which if supplied
        will be added to the match. Any parameters not
        supplied will be randomly generated.

        :param kickoff: Kickoff time (default=None)
        :type kickoff: :class:`datetime.datetime`
        :param round: Round this match is part of (default=None)
        :type round: str
        :param home: Home team (default=None)
        :type home: :class:`Team`
        :param away: Away team (default=None)
        :type away: :class:`Team`
        :param status: Match status (default=None)
        :type status: str
        :returns: Randomly generated match
        :rtype: :class:`ilc_models.Match`
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
                (home, away), (match.lineups.home, match.lineups.away)
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

                match.substitutions.extend(subs[:total_subs])

            # Cards
            for team, lineup in zip(
                (home, away), (match.lineups.home, match.lineups.away)
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
        team: Optional[str] = None,
        sub_count: int = 0,
        time: Optional[EventTime] = None,
        possible_exits: Optional[list[BasePlayer]] = None,
        possible_entries: Optional[list[BasePlayer]] = None,
    ) -> list[Substitution]:
        """Returns a randomly generated list of substitutions made within a single window.

        Any parameters not supplied will be randomly generated.

        :param team: Name of the team making this substitution (default=None)
        :type team: str
        :param sub_count: Number of substitutions to be made in this window (default=0)
        :type sub_count: str
        :param time: Time of the substitutions (default=None)
        :type time: :class:`ilc_models.EventTime`
        :param possible_exits: Players who can come off the field (default=None)
        :type possible_exits: list[:class:`ilc_models.BasePlayer`]
        :param possible_entries: Players who can come on the field (default=None)
        :type possible_entries: list[:class:`ilc_models.BasePlayer`]
        :returns: Randomly generated substitutions
        :rtype: list[:class:`ilc_models.Substitution`]
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
        team: Optional[str] = None,
        time: Optional[EventTime] = None,
        possible_exits: Optional[list[BasePlayer]] = None,
        possible_entries: Optional[list[BasePlayer]] = None,
    ) -> Substitution:
        """Returns a randomly generated substitution.

        Any parameters not supplied will be randomly generated.

        :param team: Name of the team making this substitution (default=None)
        :type team: str
        :param time: Time of the substitution (default=None)
        :type time: :class:`EventTime`
        :param possible_exits: Players who can come off the field (default=None)
        :type possible_exits: list[:class:`ilc_models.BasePlayer`]
        :param possible_entries: Players who can come on the field (default=None)
        :type possible_entries: list[:class:`ilc_models.BasePlayer`]
        :returns: Randomly generated substitution
        :rtype: :class:`ilc_models.Substitution`
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
        team: Optional[str] = None,
        time: Optional[EventTime] = None,
        players: Optional[list[BasePlayer]] = None,
    ) -> Card:
        """Returns a randomly generated red or yellow card.

        Any parameters not supplied will be randomly generated.

        :param team: Name of the team receiving this card (default=None)
        :type team: str
        :param time: Time of the card (default=None)
        :type time: :class:`ilc_models.EventTime`
        :param players: Players who can receive the card (default=None)
        :type players: list[BasePlayer]
        :returns: Randomly generated card event
        :rtype: :class:`ilc_models.Card`
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
        team: Optional[Team] = None,
        time: Optional[EventTime] = None,
        goal_type: Optional[Literal["N", "O", "P"]] = None,
        players: Optional[tuple[list[BasePlayer], list[BasePlayer]]] = None,
    ) -> Goal:
        """Returns a randomly generated goal.

        Any parameters not supplied will be randomly generated.

        :param team: Team scoring this goal (default=None)
        :type team: :class:`Team`
        :param time: Time of the goal (default=None)
        :type time: :class:`ilc_models.EventTime`
        :param goal_type: One of 'N' (normal goal), 'O' (own goal), 'P' (penalty) (default=None)
        :type goal_type: str
        :param players: Players who can score the goal as a two-item tuple,
                        the scoring team's players are the first item and
                        the opposing team's players (for own goals) are the
                        second item (default=None)
        :type players: tuple[list[:class:`ilc_models.BasePlayer`], list[:class:`ilc_models.BasePlayer`]]
        :returns: Randomly generated goal event
        :rtype: :class:`ilc_models.Goal`
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
        """Returns a randomly generated event time.

        The ``first_half_weighting`` parameter controls how likely it is
        that the time will be in the first half. A value of 50 means
        either half will have equal probability; higher values increase
        the likelihood of a first half time.

        :param first_half_weighting: Weight / 100 to give to a time in the first half
        :type first_half_weighting: int
        :returns: Randomly generated event time
        :rtype: :class:`ilc_models.EventTime`
        """
        half = 0 if random.randint(1, 100) <= first_half_weighting else 1
        time = random.randint(1, 50)
        minutes = min(time, 45) + 45 * half
        plus = max(time - 45, 0)
        return EventTime(minutes=minutes, plus=plus)

    def kickoff(self, anchor: Optional[datetime.date] = None) -> datetime.datetime:
        """Returns a randomly generated kickoff time.

        If ``anchor`` is provided the kickoff will be on that day at 15:00 or 17:30,
        the following day at 15:00, or at 19:45 on d-1, d+2 or d+3.
        This simulates a gameweek being played across a Friday to Tuesday,
        where ``anchor`` is the Saturday.

        If ``anchor`` is not provided the kickoff will be a random Saturday at 3pm.

        :param anchor: Saturday to anchor this gameweek (default=None)
        :type anchor: :class:`datetime.date`
        :returns: Randomly generated kickoff date and time
        :rtype: :class:`datetime.datetime`
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
        deltas = (
            datetime.timedelta(hours=-4, minutes=-15),  # Fri 19:45
            datetime.timedelta(hours=15),  # Sat 15:00
            datetime.timedelta(hours=17, minutes=30),  # Sat 17:30
            datetime.timedelta(days=1, hours=15),  # Sun 15:00
            datetime.timedelta(days=2, hours=19, minutes=45),  # Mon 19:45
            datetime.timedelta(days=3, hours=19, minutes=45),  # Tue 19:45
        )
        # Sat 3pm is most likely
        weights = (2, 4, 2, 1, 1, 2)
        delta = random.choices(deltas, weights, k=1)[0]

        # Make datetime object and return
        dt = datetime.datetime.combine(
            anchor, datetime.time(), tzinfo=datetime.timezone(datetime.timedelta())
        )
        return dt + delta

    def table_row(self, matches: int = 0, team: Optional[Team] = None) -> TableRow:
        """Returns a randomly generated league table row.

        Any parameters not supplied will be randomly generated.

        :param matches: Matches played (default=0)
        :type matches: int
        :param team: Team (default=None)
        :type team: :class:`Team`
        :returns: Randomly generated row from a league table
        :rtype: :class:`ilc_models.TableRow`
        """

        def weighted_results(matches: int, strength: int) -> int:
            """Get a weighted number of match results based on a team's strength.

            Higher strength will tend towards a higher return value.

            :param matches: Number of matches to play
            :type matches: int
            :param strength: Strength factor (0-5)
            :type strength: int
            :returns: Weighted random number of matches
            :rtype: int
            """
            matches_per_step = max((matches + 1) // 5, 1)
            steps = [n // matches_per_step for n in range(matches + 1)]
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

        return TableRow(
            team=team.name,
            won=won,
            drawn=drawn,
            lost=lost,
            scored=scored,
            conceded=conceded,
        )

    def league_id(self) -> int:
        """Returns a random league ID.

        :returns: Random match ID between 1 and 999
        :rtype: int
        """
        return random.randint(1, 999)

    def league_name(self) -> str:
        """Returns a randomly selected league name.

        :returns: Random league name
        :rtype: str
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
        """Returns a randomly generated league.

        If ``matches`` is False no matches will be added to the league.

        If ``games_per_opponent`` is not provided it will default to
        2 for leagues with more than 12 teams, or 4 otherwise.

        If ``split_mode`` is not provided it will default to `auto` and
        a split will occur in leagues with 3 or more games per opponent.

        Any other parameters not supplied will be randomly generated.

        :param team_count: Number of teams in this league (default=0)
        :type team_count: int
        :param matches: Whether matches should be added to this league (default=True)
        :type matches: bool
        :param games_per_opponent: Number of games to play against each other team
                                   (including post-split games) (default=0)
        :type games_per_opponent: int
        :param split_mode: One of 'none' (no split), 'auto' (auto-generated split point)
                           or 'fixed' (use split point provided) (default='auto')
        :type split_mode: str
        :param games_before_split: Number of matches to play against each opponent before
                                   the league splits in 'fixed' split mode, ignored if
                                   `split_mode` is 'none' or 'auto' (default=3)
        :type games_before_split: int
        :returns: Randomly generated league
        :rtype: :class:`ilc_models.League`
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
            date_start=datetime.date(year, 1, 1), date_end=datetime.date(year, 12, 31)
        )

        # Make sure we start on a Saturday
        start_date += datetime.timedelta(days=5 - start_date.weekday())
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
                    kickoff=self.kickoff(kickoff),
                    round=round_name,
                    home=m[0],
                    away=m[1],
                )
                for m in r
            ]
            league.rounds[round_name] = round_matches
            kickoff += datetime.timedelta(days=7)

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
                for schedule, rounds in zip(split_schedule, split_rounds):
                    inv_s = invert_schedule(schedule)
                    rounds += inv_s

            # Generate matches
            split_kickoff = kickoff + datetime.timedelta(days=7)
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

        # Adjust league end date to reflect final match
        league.end = league.matches()[-1].date.isoformat()

        return league


def match_schedule(teams: list[Team]) -> list[list[tuple[Team, Team]]]:
    """Develop a match schedule with each team playing all others once.

    Returns a list of matchdays, each containing a list of fixtures
    in the form of (home, away) tuples.

    :param teams: Teams to schedule
    :type teams: list[:class:`Team`]
    :returns: Schedule of matches
    :rtype: list[list[tuple[:class:`Team`, :class:`Team`]]]
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
            try:
                matches.append((teams[home], teams[away]))
            except IndexError:
                pass

        rounds.append(matches)

    return rounds


def invert_schedule(
    schedule: list[list[tuple[Team, Team]]],
) -> list[list[tuple[Team, Team]]]:
    """Invert all fixtures in the schedule so home becomes away and vice versa.

    Also shuffles the match days so they reoccur in a randomized order.

    :param schedule: Schedule to invert
    :type schedule: list[list[tuple[:class:`Team`, :class:`Team`]]]
    :returns: Inverted schedule
    :rtype: list[list[tuple[:class:`Team`, :class:`Team`]]]
    """
    rounds = []
    for round in schedule:
        rounds.append([(away, home) for (home, away) in round])
    random.shuffle(rounds)
    return rounds


def players_on(
    team: str, starting: list[BasePlayer], events: list[Event], time: EventTime
) -> list[BasePlayer]:
    """Returns the list of players on the pitch at a given time.

    :param team: Team name
    :type team: str
    :param starting: Starting XI
    :type starting: list[:class:`ilc_models.BasePlayer`]
    :param events: Match events
    :type events: list[:class:`ilc_models.Event`]
    :param time: Time to check
    :type time: :class:`ilc_models.EventTime`
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


def _unique_choices(
    population: MutableSequence[Any], weights: Optional[list[int]] = None, k=1
) -> list[Any]:
    """Return a `k` sized list of elements chosen from the `population` without replacement.

    :param population: Population to select elements from
    :type population: MutableSequence[Any]
    :param weights: If specified, selections are made according to the relative weights (default=None)
    :type weights: MutableSequence[int|float]
    :param k: Number of selections to return (default=1)
    :type k: int
    :returns: Selected elements
    :rtype: list[Any]
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
