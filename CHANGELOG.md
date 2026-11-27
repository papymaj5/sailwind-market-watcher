# Changelog

## [Unreleased]

### Added

- Select a trading currency and save a separate Gold Lion exchange rate for each regional currency.
- Show estimates in Gold Lions using a fixed conversion rate of 1.
- Optionally update regional exchange rates from a single Sailwind save slot.
- Optionally use the selected currency's saved wallet balance as the trade and cargo budget.

### Changed

- Skip the Windows build and release workflow for changes limited to Markdown and the legacy README screenshot.

## [v1.4.0]

### Added

- Show the app version in the bottom-right footer.
- Add a double-click Windows launcher that sets up the app's Python dependencies on first run.
- Build a standalone Windows executable on every branch push, publish branch prereleases and tagged stable releases from main, and show build status in the README.
- Run Python security linting and a build dependency vulnerability audit before packaging, including on pull requests to main.
- Filter trades by departure port after scanning markets.
- View stock and estimated single-crate prices for the selected port in the Port Market tab.
- Suggest mixed cargo for one destination using available stock, budget, cargo limits, and per-crate price changes.
- Explain market and trade tables in the README and add hover help for controls, tabs, and table headings.
- Save player inputs locally and restore them on startup.
- Report total scan time and log the time spent querying regions, reading memory, matching signatures, and loading markets.
- Show the latest successful market refresh and provide a copyable report with scan timings and read errors.
- Add offline regression tests and Ruff configuration for the Python 3.9 minimum.

### Changed

- Open Sailwind with read and query permissions only and remove unused memory-writing code.
- Collapse player settings into the toolbar, move island and profit filters onto Trade Routes, and refresh only the active tab from shared market data.
- Rename the scan button to Initialize Markets to clarify that prices refresh automatically after setup.
- Refresh the desktop UI with a dark theme and a wider trade table.
- Move market scanning off the UI thread and search for fixed bytes before checking the full signature.
- Separate the desktop UI, market logic, and player settings.
- Give each tab its own view class and share table setup across the three views.

### Fixed

- Skip unreadable markets and retry them on refresh so a failed read does not stop updates.
- Hide placeholder product slots from the market and trade tables while preserving scan offsets.
- Give scan status its own row so it does not overlap the departure-port selector.

## [v1.3.0] - 2025-10-13
### Added
- Sortable Columns. 
    Primary Sort on Origin and Destination Columns
    Secondary Sort on $Profit, $/Pound, and $/Item metrics
- Clean up and refactoring

## [v1.2.0] - 2025-10-12
### Added
- Support the 3 new Al Ankh islands. Old Ankh Town, Mirage Island and Saffron Island
- 2 New tradable items. Salt and Saffron

## [v1.1.0] - 2025-07-02
### Added
- Support for 2 new islands in latest Sailwind version
- 3 new tradeable items

### Fixed
- Fixed Emeralch Arch trades not showing because of a misname
- Removed Unneeded Library PSutil

## [v1.0.0] - 2025-06-29
### Added
- Initial release of Sailwind Market Watcher
- Trade route table and player settings input
