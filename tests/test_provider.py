"""Tests for the ilc_provider package"""

import itertools
from collections import Counter

from ilc_models import BasePlayer, Card, EventTime, Substitution
from ilc_provider import (
    _unique_choices,
    fake,
    invert_schedule,
    match_schedule,
    players_on,
    SquadPlayer,
)


class TestUniqueChoices:
    def test_returns_unique_elements(self):
        population = list(range(100))
        choices = _unique_choices(population, k=10)
        assert len(choices) == 10
        assert len(set(choices)) == 10


class TestPlayersOn:
    def test_returns_players_from_starting_lineup(self):
        team = fake.team_name()
        starting = [fake.base_player() for _ in range(11)]
        time = EventTime(minutes=60)

        # No events - should be the same list
        players = players_on(team, starting, [], time)
        assert all(player in starting for player in players)
        assert all(player in players for player in starting)

    def test_adjusts_subs(self):
        team = fake.team_name()
        starting = [fake.base_player() for _ in range(11)]
        on = fake.base_player()

        # Sub off the first player
        events = [
            Substitution(
                team=team,
                time=EventTime(minutes=30),
                player_on=on,
                player_off=starting[0],
            )
        ]
        time = EventTime(minutes=60)

        # First player should no longer be on the pitch
        players = players_on(team, starting, events, time)
        assert len(players) == 11
        assert starting[0] not in players
        assert on in players

    def test_adjusts_red_card(self):
        team = fake.team_name()
        starting = [fake.base_player() for _ in range(11)]

        # Red card for the first player
        events = [
            Card(team=team, time=EventTime(minutes=30), player=starting[0], color="R")
        ]
        time = EventTime(minutes=60)

        # First player should no longer be on the pitch
        players = players_on(team, starting, events, time)
        assert len(players) == 10
        assert starting[0] not in players

    def test_only_adjusts_after_time(self):
        team = fake.team_name()
        starting = [fake.base_player() for _ in range(11)]

        # Red card comes after the query time
        events = [
            Card(team=team, time=EventTime(minutes=80), player=starting[0], color="R")
        ]
        time = EventTime(minutes=60)

        # First player should still be on the pitch
        players = players_on(team, starting, events, time)
        assert len(players) == 11
        assert starting[0] in players


class TestMatchSchedule:
    def test_schedule_includes_all_fixtures(self):
        teams = [fake.unique.team_name() for _ in range(8)]
        schedule = match_schedule(teams)

        # Schedule should be exactly 7 rounds
        assert len(schedule) == 7

        # Each team should have exactly one match per round
        c = Counter()
        for n, round in enumerate(schedule, start=1):
            for home, away in round:
                c[home] += 1
                c[away] += 1
            assert all(v == n for v in c.values())

        # Each team should play every other team exactly once
        for team in teams:
            c = Counter()
            for round in schedule:
                for home, away in round:
                    if team == home:
                        c[away] += 1
                    elif team == away:
                        c[home] += 1
            assert len(c) == 7
            assert all(v == 1 for v in c.values())

    def test_invert_schedule_inverts_all_matches(self):
        teams = [fake.unique.team_name() for _ in range(8)]
        schedule = match_schedule(teams)
        inverted = invert_schedule(schedule)

        # Should have same number of rounds
        assert len(schedule) == len(inverted)

        # Flatten rounds
        matches = list(itertools.chain.from_iterable(schedule))
        inverted_matches = list(itertools.chain.from_iterable(inverted))
        assert len(matches) == len(inverted_matches)

        # All matches should be present in inverted form
        for home, away in matches:
            assert (away, home) in inverted_matches


class TestSquadPlayer:
    def test_base_player_returns_base_player_instance(self):
        player = SquadPlayer(11)
        base_player = player.base_player
        assert isinstance(base_player, BasePlayer)

    def test_str_includes_gk_for_keeper(self):
        player = SquadPlayer(11, keeper=True)
        assert "(GK)" in str(player)

    def test_str_doesnt_include_gk_for_non_keeper(self):
        player = SquadPlayer(11)
        assert "(GK)" not in str(player)


class TestSquad:
    def test_returns_correct_size(self):
        squad = fake.squad(size=30)
        assert len(squad) == 30

    def test_returns_correct_number_of_keepers(self):
        squad = fake.squad(keepers=4)
        keepers = sum(1 for player in squad if player.keeper)
        assert keepers == 4

    def test_shirt_numbers_are_unique(self):
        squad = fake.squad()
        shirt_numbers = [player.shirt_number for player in squad]
        assert len(shirt_numbers) == len(set(shirt_numbers))


class TestLineup:
    def test_returns_eleven_starting_players(self):
        lineup = fake.lineup()
        assert len(lineup.starting) == 11

    def test_starting_lineup_only_has_one_keeper(self):
        squad = fake.squad()
        keeper_shirts = [p.shirt_number for p in squad if p.keeper]
        lineup = fake.lineup(squad=squad)
        keepers = sum(1 for p in lineup.starting if p[0] in keeper_shirts)
        assert keepers == 1


class TestMatch:
    def test_unplayed_match_has_no_lineups_or_events(self):
        match = fake.match(status="NS")
        assert not match.lineups
        assert not match.events()

    def test_completed_match_has_lineups_and_events(self):
        match = fake.match()
        assert match.lineups
        assert match.events()

    def test_correct_goal_events(self):
        match = fake.match()
        home = away = 0
        for goal in match.goals:
            assert goal.team in (match.teams.home, match.teams.away)
            if goal.team == match.teams.home:
                home += 1
            elif goal.team == match.teams.away:
                away += 1
        assert home == match.score.home
        assert away == match.score.away
