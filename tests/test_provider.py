"""Tests for the ilc_provider package"""

import datetime
import itertools
import random
from collections import Counter

import pytest
from ilc_models import BasePlayer, Card, EventTime, Substitution

from ilc_provider import (
    ILCProvider,
    SquadPlayer,
    Team,
    _unique_choices,
    fake,
    invert_schedule,
    match_schedule,
    players_on,
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
        players = players_on(team, starting, events, time)  # type: ignore
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
        players = players_on(team, starting, events, time)  # type: ignore
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
        players = players_on(team, starting, events, time)  # type: ignore
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


def _age(dob: str, on: datetime.date) -> int:
    """Return the exact age in years of someone born on `dob` as of `on`."""
    born = datetime.date.fromisoformat(dob)
    return on.year - born.year - ((on.month, on.day) < (born.month, born.day))


class TestPlayer:
    def test_player_id_has_no_hidden_uniqueness(self, monkeypatch):
        values = iter([42, 42])
        monkeypatch.setattr(random, "randint", lambda a, b: next(values))

        assert [fake.player_id(), fake.player_id()] == [42, 42]

    def test_player_has_reasonable_dob(self):
        active_date = datetime.date(2000, 1, 1)
        player = fake.player(active_date=active_date)

        # Player should be between 17 and 35 years old on 1 Jan 2000
        assert 17 <= _age(player.dob, active_date) <= 35

    @pytest.mark.parametrize(
        "active_date", [datetime.date(2000, 6, 15), datetime.date(2000, 2, 29)]
    )
    @pytest.mark.parametrize(("age", "pick"), [(17, "end_date"), (35, "start_date")])
    def test_dob_gives_exact_age_at_window_edges(
        self, monkeypatch, active_date, age, pick
    ):
        monkeypatch.setattr(random, "choices", lambda *args, **kwargs: [age])
        monkeypatch.setattr(fake, "date_between", lambda **kw: kw[pick])
        player = fake.player(active_date=active_date)
        assert _age(player.dob, active_date) == age


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
        active_date = datetime.date(2000, 1, 1)
        player = SquadPlayer(11, active_date=active_date)

        # Player should be between 17 and 35 years old
        # on 1 Jan 2000
        assert 17 <= _age(player.player.dob, active_date) <= 35


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
        active_date = datetime.date(2000, 1, 1)
        squad = fake.squad(active_date=active_date)
        for player in squad:
            # Player should be between 17 and 35 years old
            # on 1 Jan 2000
            assert 17 <= _age(player.player.dob, active_date) <= 35


class TestTeam:
    def test_players_have_reasonable_dobs(self):
        active_date = datetime.date(2000, 1, 1)
        team = Team(active_date=active_date)
        for player in team.squad:
            # Player should be between 17 and 35 years old
            # on 1 Jan 2000
            assert 17 <= _age(player.player.dob, active_date) <= 35


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
            if goal.team == match.teams.home:  # pragma: no cover
                home += 1
            else:  # pragma: no cover
                away += 1

        # Goal events should match the score
        assert home == match.score.home
        assert away == match.score.away

    def test_at_most_three_sub_windows_per_team(self, monkeypatch):
        # Make unforced windows as small as possible so a limit breach is likely
        original = ILCProvider.sub_window

        def one_sub_window(self, *args, sub_count=0, **kwargs):
            return original(self, *args, sub_count=sub_count or 1, **kwargs)

        monkeypatch.setattr(ILCProvider, "sub_window", one_sub_window)

        for _ in range(50):
            match = fake.match()
            for team in (match.teams.home, match.teams.away):
                times = {
                    (s.time.minutes, s.time.plus)
                    for s in match.substitutions
                    if s.team == team
                }
                assert len(times) <= 3

    def test_sent_off_players_are_not_carded_again(self, monkeypatch):
        sent_off = set()

        def red_card(self, team, time, players):
            player = players[0]
            assert (team, player.player_id) not in sent_off
            sent_off.add((team, player.player_id))
            return Card(team=team, time=time, color="R", player=player)

        monkeypatch.setattr(ILCProvider, "card", red_card)

        for _ in range(20):
            fake.match()

        assert sent_off


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

    def test_midweek_kickoff_is_tuesday_or_wednesday_evening(self):
        anchor = datetime.date(2024, 1, 2)
        for _ in range(20):
            kickoff = fake.kickoff(anchor=anchor, midweek=True)
            assert kickoff.weekday() in (1, 2)
            assert kickoff.time() == datetime.time(19, 45)


class TestTableRow:
    def test_row_has_correct_number_of_matches(self):
        row = fake.table_row(matches=10)
        assert row.played == 10

    def test_adds_form(self):
        row = fake.table_row(matches=5)
        assert len(row.form) == 5

    def test_adds_correct_results_to_form(self):
        row = fake.table_row(matches=5)
        assert row.form.count("W") == row.won
        assert row.form.count("D") == row.drawn
        assert row.form.count("L") == row.lost

    def test_fewer_matches_gives_shorter_form(self):
        row = fake.table_row(matches=3)
        assert len(row.form) == 3

    def test_result_weights_are_never_negative(self, monkeypatch):
        sample = random.sample
        counts_seen = []

        def recording_sample(population, k, *, counts=None):
            if counts is not None:
                counts_seen.append(list(counts))
            return sample(population, k, counts=counts)

        monkeypatch.setattr(random, "sample", recording_sample)
        team = Team()
        for strength in range(6):
            team.strength = strength
            for matches in range(1, 39):
                fake.table_row(matches=matches, team=team)
        assert all(c >= 0 for counts in counts_seen for c in counts)


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

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"team_count": 4, "games_per_opponent": 4, "split_mode": "none"},
            {
                "team_count": 4,
                "games_per_opponent": 2,
                "split_mode": "fixed",
                "games_before_split": 1,
            },
        ],
    )
    def test_rounds_kick_off_on_matching_days(self, kwargs):
        league = fake.league(**kwargs)
        for round_matches in league.rounds.values():
            kickoffs = [
                datetime.datetime.fromisoformat(m.kickoff) for m in round_matches
            ]
            weekend = all(k.weekday() in (4, 5, 6) for k in kickoffs)
            midweek = all(
                k.weekday() in (1, 2) and k.time() == datetime.time(19, 45)
                for k in kickoffs
            )
            assert weekend or midweek

    @pytest.mark.parametrize(
        ("year", "pick"),
        [("2023", "date_start"), ("2024", "date_end")],
    )
    def test_start_is_first_match_in_league_year(self, monkeypatch, year, pick):
        monkeypatch.setattr(fake, "year", lambda: year)
        monkeypatch.setattr(fake, "date_between_dates", lambda **kw: kw[pick])
        league = fake.league(team_count=4, games_per_opponent=2)
        assert league.start == league.matches()[0].date.isoformat()
        assert int(league.start[:4]) == league.year

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

    @pytest.mark.parametrize("games_before_split", [2, 3])
    def test_fixed_split_must_leave_games_after_split(self, games_before_split):
        with pytest.raises(ValueError):
            fake.league(
                team_count=4,
                games_per_opponent=2,
                split_mode="fixed",
                games_before_split=games_before_split,
            )

    def test_post_split_home_and_away_alternate(self):
        # 2 games pre-split and 4 post-split, so every pair plays an equal
        # number of home and away games
        league = fake.league(
            team_count=8,
            games_per_opponent=6,
            split_mode="fixed",
            games_before_split=2,
        )
        names = [row[0] for row in league.table()]
        for home, away in itertools.combinations(names, 2):
            h2h = league.head_to_head((home, away))
            home_count = sum(m.teams.home == home for m in h2h)
            assert home_count * 2 == len(h2h)

    def test_players_have_reasonable_dobs(self):
        league = fake.league(matches=False)
        min_year = league.year - 36
        max_year = league.year - 16

        for player in league.players.values():
            # Players should be between 17 and 35 years old
            year = int(player.dob[:4])
            assert year >= min_year
            assert year <= max_year

    def test_league_lasts_less_than_nine_months(self):
        league = fake.league(team_count=24)
        duration = datetime.date.fromisoformat(
            league.end
        ) - datetime.date.fromisoformat(league.start)
        assert duration.days < 270

    def test_no_team_has_more_than_one_match_per_day(self):
        league = fake.league(team_count=8)
        team = random.choice(league.teams)
        dates = set()
        for match in league.matches(team=team):
            assert match.date not in dates
            dates.add(match.date)


class TestUser:
    def test_username_is_first_part_of_email(self):
        user = fake.user()
        assert user.email.startswith(user.username)

    def test_password_is_correctly_stored(self):
        password = fake.password()
        user = fake.user(password=password)
        assert user.verify_password(password)
