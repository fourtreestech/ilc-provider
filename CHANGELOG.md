# Changelog

## [Unreleased]

### Added

- Add `midweek` option to `kickoff` for Tuesday/Wednesday 19:45 kickoffs
- Support Python 3.14

### Changed

- `league` raises `ValueError` in `fixed` split mode if `games_before_split` is not less than `games_per_opponent`
- `player_id` no longer guarantees unique IDs itself - uniqueness comes from `fake.unique`
- Require `ilc-models>=0.3.1`

### Fixed

- Ensure a team makes substitutions in at most three windows
- Alternate home and away across repeated post-split fixtures
- Ensure `table_row` result weights are never negative
- Use Tuesday/Wednesday evening kickoff times for Tuesday rounds
- Ensure league start stays within its year and matches the first match date
- Ensure generated dates of birth give the exact intended age

## [0.1.3] - 2025-11-15

### Fixed

- Ensure a team has only one match per day

## [0.1.2] - 2025-11-14

### Changed

- Add form to `table_row` provider

### Fixed

- Ensure a season lasts less than 9 months

## [0.1.1] - 2025-04-04

### Fixed

- Ensure league generates players with reasonable DOBs


## [0.1.0] - 2025-04-03

_Initial release._

[Unreleased]: https://github.com/fourtreestech/ilc-provider/compare/v0.1.3...HEAD

[0.1.3]: https://github.com/fourtreestech/ilc-provider/releases/tag/v0.1.3

[0.1.2]: https://github.com/fourtreestech/ilc-provider/releases/tag/v0.1.2

[0.1.1]: https://github.com/fourtreestech/ilc-provider/releases/tag/v0.1.1

[0.1.0]: https://github.com/fourtreestech/ilc-provider/releases/tag/v0.1.0
