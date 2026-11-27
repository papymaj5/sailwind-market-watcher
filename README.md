# ⛵ Sailwind Market Watcher
[![Windows build](https://github.com/papymaj5/sailwind-market-watcher/actions/workflows/build-windows.yml/badge.svg?branch=main&event=push)](https://github.com/papymaj5/sailwind-market-watcher/actions/workflows/build-windows.yml)

A real-time market and trade route analyzer for the open-world sailing game **Sailwind**.

The watcher reads market stock from the running game and estimates prices and profits for trades between ports.

---

🚀 **How to Use**

1. Launch Sailwind and load your save.
2. Open the [Windows executable](#standalone-windows-executable) or double-click **Launch Market Watcher.bat** if you’re running from source.
3. Click **Initialize Markets** once per game session.
4. In **Settings**, select your trading currency, enter your cargo limits, and click **Update Values**. Enter your current cash and exchange rate, or enable [saved cash and rates](#currency-conversion).
5. Choose a **Departure port**. Open **Port Market** to check stock, **Trade Routes** to compare destinations, or **Cargo Plan** to plan a mixed load for one destination.

### Read the Port Market

After scanning, choose a **Departure port** such as **Gold Rock City**, then
open **Port Market**. Hover over a column heading for a quick explanation.

| Column | What it shows |
| --- | --- |
| **Product** | The commodity at the selected port. |
| **Stock** | The estimated number of crates available to buy. A zero means none are available. |
| **Est. Buy / Crate** | What you would pay for the next crate. A dash means the good is out of stock. |
| **Est. Sell / Crate** | What the port would pay for one crate you already own. A port can have a sell quote even when its stock is zero. |

For example, **Stock 21**, **Buy 247**, and **Sell 242** means the port has an
estimated 21 crates for sale, the next one would cost about 247, and the port
would pay about 242 for one crate you sell. Prices can change as you buy or
sell, so multiplying a one-crate price by the quantity gives a rough estimate.

### Read Trade Routes

Use **Port Market** to check what is available locally. Switch to **Trade
Routes** to see where you could sell it and what you might earn on the planned
load. In **Qnty**, a value like **5/21** means the route uses 5 of the estimated
21 crates available at the departure port. **$Buy**, **$Sell**, and **$Profit**
are totals for those 5 crates. The budget, cargo limits, and minimum profit
filter apply to this tab.

Choose a specific **Departure port** to plan trades from that port. Choose
**Selected start groups** to browse departures by region. Open **Filters** on
the Trade Routes tab to change **End Groups** or **Min Profit**. Open
**Settings** in the toolbar to change cash, exchange rate, or cargo limits,
then click **Update Values** to apply and save them.

### Plan a mixed cargo load

Choose a **Departure port**, open **Cargo Plan**, and pick one destination.
The planner suggests a mix of goods within your available money, weight, and
cargo volume, and shows estimated totals for the load. It considers profitable
crates even if the **Trade Routes** minimum profit filter would hide them.

The watcher estimates each crate separately. Buying reduces supply at the
departure port and selling adds supply at the destination. The planner weighs
each additional crate's estimated profit against the budget and space it uses.
The suggested load is a heuristic, so another mix can sometimes earn more.

**Initialize Markets** locates the markets. The watcher then rereads supply
about every five seconds. When you sail to another port, just change
**Departure port**. If you restart Sailwind, restart the watcher and initialize
the markets again.

The scan area shows how many markets loaded and the time of the last successful
refresh. If a market becomes unreadable, the watcher leaves it out of trade
estimates and retries it on the next refresh. Use **Diagnostics → Copy diagnostics** to copy
the latest scan timings, readable market count, and read errors for a bug report.

---

## 📌 Features

✅ **Live Memory Scan**\
Locates 32 expected markets, then refreshes their stock data and recalculates price estimates.

💰 **Profit-Driven Trade Routes**\
Browse trades and sort them by:

- Total profit
- Profit per pound (weight)
- Profit per item

🎯 **Player-Conscious Filtering**\
Takes into account your current:

- Money
- Cargo mass & volume limits
- Minimum profit threshold

🌎 **Regional Trade Planning**\
Select specific **start** and **destination** island groups to tailor your strategy.

🖼️ **Interactive GUI**\
The three views include:

- Sortable Columns for simple analytics
- Live-updating trade table
- Tooltips for helpful guidance
- Input fields for cargo & currency

---

💡 **Development** This project is written in Python using:

- `tkinter` for the GUI
- `pymem` for memory access
- `Pillow` for image icons

Run the offline tests and code checks from the repository folder:

```powershell
python -m pip install -r requirements.txt ruff
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
```

For a live Sailwind 0.41 check, load your save at Gold Rock City and scan from
PowerShell. Compare Goods stock and a one-crate purchase quote with the current
in-game market. The offline pricing tests use synthetic supply values. The
console reports separate timings for region queries, memory reads, signature
matching, and market loading.

See [CHANGELOG.md](CHANGELOG.md) for changes in progress and release history.

### Build and security checks

GitHub Actions runs Ruff's Python security rules, audits the installed Windows
build dependencies with pip-audit, runs the regression suite, and smoke-tests
the packaged executable. These checks run on branch pushes and pull requests
to main when the changes include files beyond Markdown and the legacy README
screenshot. Release publishing waits for a successful build.

Market Watcher requests Windows process read and query access to Sailwind.
The checks follow parts of the
[NIST Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final),
including source analysis, dependency review, and testing the executable.

---

### How it works

Market Watcher opens `Sailwind.exe` with read and query access and locates the
markets using a known byte pattern. It reads stock from game memory and uses
configured product values, the selected exchange rate, and a supply-based
pricing model to estimate buy and sell prices. Check the in-game quote when
placing a trade.

---

### Currency conversion

1. Open **Settings** and select the same **Currency** you use for trades in Sailwind.
2. At a currency exchange, select **Gold Lions** under **Sell** and your trading currency under **Buy**.
3. Enter the posted rate in **Per Gold Lion** and click **Update Values**. You can read the rate without exchanging money.

The watcher remembers a separate rate for each currency. The defaults are
34.22 Al’Ankh Lions, 82 Aestrin Crowns, and 330 Emerald Dragons per Gold Lion.
Choose **Gold Lions** to express estimates in Gold Lions with a fixed rate of 1.
Use the current in-game quote when available. When switching currencies, enter
your corresponding balance in **Player Principal**.

For a single local Sailwind 0.41 save slot, enable **Use exchange rates from
save** in Settings. The watcher refreshes the rates after a save or autosave.
If the save is unavailable or there are multiple slots, the watcher uses your
manually saved rate. Turning the option off also restores your manual rate.
Enable **Use cash balance from save** to use the selected currency's saved
wallet balance for Trade Routes and Cargo Plan. It refreshes after a save or
autosave and falls back to your manual budget if there is no unambiguous save.

---

## 🧰 Requirements

- 64-bit Windows for the packaged executable
- [**Sailwind** on Steam](https://store.steampowered.com/app/1764530/Sailwind) version 0.41
- Python 3.9+, Pymem, and Pillow if you run from source

## 🐍 Installation Guide (Windows)

### Standalone Windows executable

Download **SailwindMarketWatcher-Windows-x64.zip** from [Releases](https://github.com/papymaj5/sailwind-market-watcher/releases). Extract it, load your Sailwind save, and double-click `SailwindMarketWatcher.exe`. The executable bundles Python and the app dependencies.

Branch pushes with build changes run the tests and build the executable.
Successful builds from branches such as `dev` publish prereleases. A successful
push build on `main`, including a merged pull request, publishes a stable release
and creates a tag from the version in
`pyproject.toml`. Bump that version before merging the next stable release.
If the release already exists, the new build is still available in the run's
**Artifacts**. Manual runs from **Actions → Build Windows executable → Run workflow**
produce artifacts without publishing a release.

### Python launcher

Install Python 3.9 or newer, extract the project to a writable folder, and load your Sailwind save. Double-click **Launch Market Watcher.bat** in the project folder. The first launch needs internet access to install Pymem and Pillow into a local `.venv`. Later launches reuse that environment. The console stays open while the app runs so you can see scan timings and errors.

### Run from PowerShell

To run from source without the double-click launcher, download the source ZIP
from [this fork](https://github.com/papymaj5/sailwind-market-watcher) or clone
it. Open PowerShell in the extracted or cloned folder, then run:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Load a save in Sailwind before opening the watcher.

## 🐞 Troubleshooting

- **Sailwind is not running** — Load a save in Sailwind, then reopen Market Watcher.
- **Market initialization failed** — Use **Diagnostics → Copy diagnostics** to capture the detected market count and any read errors.
- **Saved rates or balance did not update** — Save in Sailwind and give the watcher a few seconds to refresh. With multiple local slots, enter the rate or balance manually.
- **Prices differ from Sailwind** — Check the selected currency and its rate per Gold Lion. The watcher uses a supply-based estimate, so check the game’s quote before trading.

## 📜 License

MIT License. See [LICENSE](LICENSE) file.
