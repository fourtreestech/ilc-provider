"""Tests for the ilc_provider package"""

import datetime
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
    Team,
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

    def test_schedule_manage_odd_number_of_teams(self):
        teams = [fake.unique.team_name() for _ in range(7)]
        schedule = match_schedule(teams)

        # Schedule should be exactly 7 rounds
        assert len(schedule) == 7

        # Each team should play every other team exactly once
        for team in teams:
            c = Counter()
            for round in schedule:
                for home, away in round:
                    if team == home:
                        c[away] += 1
                    elif team == away:
                        c[home] += 1
            assert len(c) == 6
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


class TestPlayer:
    def test_player_has_reasonable_dob(self):
        player = fake.player(active_date=datetime.date(2000, 1, 1))

        # Player should be between 17 and 35 years old
        # on 1 Jan 2000
        year = int(player.dob[:4])
        assert year >= 1965
        assert year <= 1983


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

    def test_player_has_reasonable_dob(self):
        player = SquadPlayer(11, active_date=datetime.date(2000, 1, 1))

        # Player should be between 17 and 35 years old
        # on 1 Jan 2000
        year = int(player.player.dob[:4])
        assert year >= 1965
        assert year <= 1983


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

    def test_players_have_reasonable_dobs(self):
        squad = fake.squad(active_date=datetime.date(2000, 1, 1))
        for player in squad:
            # Player should be between 17 and 35 years old
            # on 1 Jan 2000
            year = int(player.player.dob[:4])
            assert year >= 1965
            assert year <= 1983


class TestTeam:
    def test_players_have_reasonable_dobs(self):
        team = Team(active_date=datetime.date(2000, 1, 1))
        for player in team.squad:
            # Player should be between 17 and 35 years old
            # on 1 Jan 2000
            year = int(player.player.dob[:4])
            assert year >= 1965
            assert year <= 1983


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
        # Count the goal events for each team
        for goal in match.goals:
            assert goal.team in (match.teams.home, match.teams.away)
            if goal.team == match.teams.home:
                home += 1
            else:
                away += 1

        # Goal events should match the score
        assert home == match.score.home
        assert away == match.score.away


class TestEvents:
    def test_substitution_uses_correct_players(self):
        on = [fake.base_player() for _ in range(5)]
        subs = [fake.base_player() for _ in range(5)]
        sub = fake.substitution(possible_exits=on, possible_entries=subs)
        assert sub.player_on in subs
        assert sub.player_off in on

    def test_sub_window_uses_correct_players(self):
        on = [fake.base_player() for _ in range(5)]
        subs = [fake.base_player() for _ in range(5)]
        window = fake.sub_window(possible_exits=on, possible_entries=subs)
        for sub in window:
            assert sub.player_on in subs
            assert sub.player_off in on

    def test_sub_window_generates_correct_number_of_subs(self):
        window = fake.sub_window(sub_count=3)
        assert len(window) == 3

    def test_all_subs_in_window_have_the_same_time(self):
        window = fake.sub_window(sub_count=3)
        time = window[0].time
        for sub in window[1:]:
            assert sub.time == time

    def test_all_subs_in_window_have_the_same_team(self):
        window = fake.sub_window(sub_count=3)
        team = window[0].team
        for sub in window[1:]:
            assert sub.team == team

    def test_goal_is_scored_by_correct_team(self):
        # Build teams and get players for each
        team = fake.team()
        team_lineup = fake.lineup(team.squad)
        team_players = [p[1] for p in team_lineup.starting]

        opp = fake.team()
        opp_lineup = fake.lineup(opp.squad)
        opp_players = [p[1] for p in opp_lineup.starting]

        # Goal should be scored by one of the players from `team`
        goal = fake.goal(team=team, goal_type="N", players=(team_players, opp_players))
        assert goal.scorer in team_players

    def test_own_goal_is_scored_by_correct_team(self):
        # Build teams and get players for each
        team = fake.team()
        team_lineup = fake.lineup(team.squad)
        team_players = [p[1] for p in team_lineup.starting]

        opp = fake.team()
        opp_lineup = fake.lineup(opp.squad)
        opp_players = [p[1] for p in opp_lineup.starting]

        # Goal should be scored by one of the players from `team`
        goal = fake.goal(team=team, goal_type="O", players=(team_players, opp_players))
        assert goal.scorer in opp_players

    def test_scorer_taken_from_team_squad(self):
        team = fake.team()
        players = [p.base_player for p in team.squad]
        goal = fake.goal(team=team, goal_type="N")
        assert goal.scorer in players

    def test_event_time_from_first_half(self):
        time = fake.event_time(first_half_weighting=100)
        assert time.minutes < 46

    def test_event_time_from_second_half(self):
        time = fake.event_time(first_half_weighting=0)
        assert time.minutes > 45


class TestKickoff:
    def test_kickoff_is_on_a_saturday(self):
        kickoff = fake.kickoff()
        assert kickoff.weekday() == 5

    def test_kickoff_is_close_to_anchor(self):
        anchor = datetime.date.today()
        kickoff = fake.kickoff(anchor=anchor)
        assert abs((anchor - kickoff.date()).days) < 4


class TestTableRow:
    def test_row_has_correct_number_of_matches(self):
        row = fake.table_row(matches=10)
        assert row.played == 10


class TestLeague:
    def test_no_matches(self):
        league = fake.league(matches=False)
        assert not league.matches()

    def test_no_split_match_count(self):
        league = fake.league(team_count=8, games_per_opponent=2)
        table = league.table()
        # 2 games per opponent = 14 matches for each team
        for row in table:
            assert row[1] == 14

    def test_split_match_count(self):
        league = fake.league(team_count=8, games_per_opponent=4)
        table = league.table()
        # 4 games per opponent = 21 pre-split, 3 post-split
        assert league.split == 21
        for row in table:
            assert row[1] == 24

    def test_split_mode_none(self):
        league = fake.league(team_count=8, games_per_opponent=4, split_mode="none")
        table = league.table()
        # 4 games per opponent = 28 in total
        for row in table:
            assert row[1] == 28

    def test_six_matches_splits_at_four(self):
        league = fake.league(team_count=8, games_per_opponent=6)
        table = league.table()
        # 6 games per opponent = 28 pre-split, 6 after
        assert league.split == 28
        for row in table:
            assert row[1] == 34

    def test_players_have_reasonable_dobs(self):
        league = fake.league(matches=False)
        min_year = league.year - 36
        max_year = league.year - 16

        for player in league.players.values():
            # Players should be between 17 and 35 years old
            year = int(player.dob[:4])
            assert year >= min_year
            assert year <= max_year
