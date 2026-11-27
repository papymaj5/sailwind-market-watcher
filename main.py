"""Launch the Sailwind Market Watcher desktop application."""

import ctypes
import math
import tkinter as tk
from copy import copy
from datetime import datetime
from queue import Empty, Queue
from threading import Thread
from time import perf_counter
from tkinter import ttk

import pymem
from PIL import Image, ImageTk

from market import (
    Market,
    refresh_markets,
    scan_market_addresses,
)
from memhack import open_read_only_process
from save_economy import SavedGameEconomy, SaveEconomy
from settings import (
    APP_DIR,
    APP_VERSION,
    GOLD_CURRENCY,
    PLAYER_SETTINGS_PATH,
    Player,
    save_player_settings,
)
from views import (
    CargoPlanView,
    PortMarketView,
    TradeRoutesView,
    create_tooltip,
    toggle_panel,
)

START_GROUPS_OPTION = "Selected start groups"


def configure_theme(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    background = "#0e1724"
    panel = "#172437"
    field = "#101c2d"
    border = "#30435a"
    text_color = "#edf4fc"
    muted = "#aabdd2"
    accent = "#79e1cf"
    root.configure(background=background)
    root.option_add("*TCombobox*Listbox.background", field)
    root.option_add("*TCombobox*Listbox.foreground", text_color)
    root.option_add("*TCombobox*Listbox.selectBackground", "#28566a")
    root.option_add("*TCombobox*Listbox.selectForeground", text_color)
    root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))

    style.configure(".", background=panel, foreground=text_color, font=("Segoe UI", 10))
    style.configure("Page.TFrame", background=background)
    style.configure("TNotebook", background=background, borderwidth=0)
    style.configure("TNotebook.Tab", background="#21334a", padding=(14, 7))
    style.map(
        "TNotebook.Tab",
        background=[("selected", panel)],
        foreground=[("selected", accent)],
    )
    style.configure(
        "TLabelframe", bordercolor=border, lightcolor=border, darkcolor=border
    )
    style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
    style.configure("Muted.TLabel", foreground=muted)
    style.configure("Footer.TLabel", background=background, foreground=muted)
    style.configure("Tooltip.TLabel", background="#263b52")
    style.configure(
        "TButton",
        background="#263b52",
        bordercolor=border,
        lightcolor="#263b52",
        darkcolor="#263b52",
        padding=(12, 6),
    )
    style.map(
        "TButton",
        background=[("pressed", "#304d66"), ("active", "#34526b")],
        bordercolor=[("focus", accent)],
        foreground=[("disabled", muted)],
    )
    style.configure(
        "Accent.TButton",
        background=accent,
        foreground="#102631",
        lightcolor=accent,
        darkcolor=accent,
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Accent.TButton",
        background=[
            ("disabled", "#263b52"),
            ("pressed", "#55bcae"),
            ("active", "#a2eddf"),
        ],
        foreground=[("disabled", muted)],
    )
    for input_style in ("TEntry", "TCombobox"):
        style.configure(
            input_style,
            fieldbackground=field,
            insertcolor=text_color,
            bordercolor=border,
            lightcolor=field,
            darkcolor=field,
            arrowcolor=text_color,
            padding=(7, 4),
        )
        style.map(
            input_style,
            fieldbackground=[("readonly", field), ("disabled", panel)],
            foreground=[("disabled", muted)],
            bordercolor=[("focus", accent)],
        )
    style.configure(
        "TCheckbutton",
        indicatorbackground=field,
        indicatorforeground="#102631",
        indicatorcolor=field,
        indicatormargin=(0, 0, 5, 0),
        padding=(2, 3),
    )
    style.map(
        "TCheckbutton",
        indicatorbackground=[("selected", accent)],
        indicatorcolor=[("selected", accent)],
        background=[("active", "#263b52")],
    )
    style.configure(
        "Treeview",
        background=field,
        fieldbackground=field,
        bordercolor=border,
        lightcolor=field,
        darkcolor=field,
        rowheight=30,
    )
    style.map(
        "Treeview",
        background=[("selected", "#28566a")],
        foreground=[("selected", "#ffffff")],
    )
    style.configure(
        "Treeview.Heading",
        font=("Segoe UI", 10, "bold"),
        background="#21334a",
        bordercolor=border,
        lightcolor="#21334a",
        darkcolor="#21334a",
        padding=(7, 8),
    )
    style.map("Treeview.Heading", background=[("active", "#34526b")])
    style.configure(
        "Vertical.TScrollbar",
        background="#34526b",
        troughcolor=field,
        bordercolor=field,
        lightcolor="#34526b",
        darkcolor="#34526b",
        arrowcolor=text_color,
    )


def main():
    scan_report = ["Markets have not been initialized."]
    refresh_report = ["No refresh yet."]
    last_refresh = None
    readable_markets = []
    saved_game_economy = SavedGameEconomy()
    automatic_rate = None
    automatic_balance = None

    def copy_diagnostics():
        root.clipboard_clear()
        root.clipboard_append(
            "\n".join(
                ["Sailwind Market Watcher diagnostics", *scan_report, *refresh_report]
            )
        )
        diagnostics_button.config(text="Copied")
        root.after(1600, lambda: diagnostics_button.config(text="Diagnostics"))

    def find_markets():
        results = Queue()
        started_at = perf_counter()
        start_button.state(["disabled"])
        status_label.config(text="Initializing market list…")

        def scan():
            report = []
            try:
                scan_result = scan_market_addresses(pm.process_handle)
                addresses = scan_result.addresses
                report.append(
                    f"Scan timing: region queries {scan_result.region_query_seconds:.2f}s, "
                    f"memory reads {scan_result.memory_read_seconds:.2f}s, "
                    f"signature matching {scan_result.signature_match_seconds:.2f}s."
                )
                if len(addresses) != 32:
                    raise ValueError(f"Found {len(addresses)} markets, expected 32.")
                load_started_at = perf_counter()
                scanned_markets = []
                for slot, address in enumerate(addresses, start=1):
                    try:
                        market = Market(pm, address - 0x4E)
                        if market.name == "Unknown Market":
                            raise ValueError("Market name could not be read.")
                    except (
                        pymem.exception.PymemError,
                        ValueError,
                        OverflowError,
                    ) as error:
                        report.append(f"Market slot {slot}: {error}")
                    else:
                        scanned_markets.append(market)
                report.append(
                    f"Market loading took {perf_counter() - load_started_at:.2f}s."
                )
                if not scanned_markets:
                    raise ValueError("None of the market records could be read.")
                results.put((scanned_markets, report))
            except Exception as error:
                report.append(f"Market scan failed: {error}")
                results.put((None, report))

        def finish_scan():
            try:
                result, report = results.get_nowait()
            except Empty:
                root.after(100, finish_scan)
                return

            start_button.state(["!disabled"])
            elapsed = perf_counter() - started_at
            scan_report[:] = [
                f"Initialization finished at {datetime.now():%H:%M:%S} in {elapsed:.1f}s.",
                *report,
            ]
            print("\n".join(scan_report))
            if result is None:
                status_label.config(
                    text="Market initialization failed. Copy diagnostics for details."
                )
                return

            markets[:] = result
            summary = f"Loaded {len(markets)} of 32 markets in {elapsed:.1f} seconds."
            scan_report.append(summary)
            status_label.config(text=summary)
            print(summary)
            for market in markets:
                print(f"{hex(market.base)}  {market.index:02} {market.name}")
            port_names = sorted(
                {market.name for market in markets if market.name != "Unknown Market"}
            )
            origin_port_picker.configure(
                values=[START_GROUPS_OPTION, *port_names], state="readonly"
            )
            if origin_port_var.get() not in port_names:
                origin_port_var.set(START_GROUPS_OPTION)
            refresh_market_data()

        Thread(target=scan, daemon=True).start()
        root.after(100, finish_scan)

    def update_values(inputs, settings_status):
        try:
            changes = {key: float(var.get()) for key, var in inputs.items()}
            if not all(map(math.isfinite, changes.values())):
                raise ValueError
        except ValueError:
            settings_status.config(text="Enter a number in each field.")
            return

        rate = changes.pop("conversion_rate", None)
        if automatic_balance is not None:
            changes.pop("principal", None)
        if (
            rate is not None
            and player.currency != GOLD_CURRENCY
            and automatic_rate is None
        ):
            if rate <= 0:
                settings_status.config(text="Enter a rate greater than zero.")
                return
            player.conversion_rates[player.currency] = rate
        player.update(**(vars(player) | changes))
        save_and_refresh(settings_status)

    def save_and_refresh(settings_status):
        try:
            save_player_settings(PLAYER_SETTINGS_PATH, vars(player))
        except OSError as error:
            settings_status.config(text="Applied for this session only.")
            print(f"Could not save player settings: {error}")
        else:
            settings_status.config(text="Saved.")
        refresh_market_data()

    def refresh_market_data():
        nonlocal last_refresh, readable_markets, automatic_rate, automatic_balance
        previous_rate = automatic_rate
        previous_balance = automatic_balance
        economy, source = (
            saved_game_economy.read()
            if player.auto_rates or player.auto_balance
            else (SaveEconomy(), "")
        )
        automatic_rate = (
            economy.rates.get(player.currency) if player.auto_rates else None
        )
        automatic_balance = (
            economy.balances.get(player.currency) if player.auto_balance else None
        )
        if automatic_balance is not None:
            balance_source.config(text=f"Save balance · {source}")
        elif player.auto_balance:
            balance_source.config(text=f"Using manual balance. {source}")
        else:
            balance_source.config(text="")
        principal_entry.configure(
            state="readonly" if automatic_balance is not None else "normal"
        )
        if automatic_balance is not None or previous_balance is not None:
            player_vars["principal"].set(budget())
        if player.currency == GOLD_CURRENCY:
            rate_source.config(text="Gold Lion rate is fixed at 1.")
        elif automatic_rate is not None:
            rate_source.config(text=f"Save rate · {source}")
        elif player.auto_rates:
            rate_source.config(text=f"Using manual rate. {source}")
        else:
            rate_source.config(text="")
        rate_entry.configure(
            state="readonly"
            if automatic_rate is not None or player.currency == GOLD_CURRENCY
            else "normal"
        )
        if (
            automatic_rate is not None
            or previous_rate is not None
            or player.currency == GOLD_CURRENCY
        ):
            player_vars["conversion_rate"].set(automatic_rate or player.conversion_rate)
        update_player_summary()
        if not markets:
            return

        readable_markets, read_errors = refresh_markets(
            markets,
            automatic_rate if automatic_rate is not None else player.conversion_rate,
        )
        if readable_markets:
            last_refresh = datetime.now()
        time_label = (
            f"Last refresh {last_refresh:%H:%M:%S}"
            if last_refresh
            else "No successful refresh"
        )
        refresh_summary = f"{time_label} · {len(readable_markets)}/{len(markets)} loaded markets readable"
        refresh_status.config(text=refresh_summary)
        refresh_report[:] = [refresh_summary, *read_errors]
        update_chart()

    def update_chart():
        if not markets:
            return

        origin_name = origin_port_var.get()
        if origin_name == START_GROUPS_OPTION:
            origin_name = None
        active_tab = tabs.select()
        planning_player = copy(player)
        planning_player.principal = budget()
        if active_tab == str(routes_view):
            routes_view.render(origin_name, readable_markets, planning_player)
            return

        origin = next(
            (market for market in readable_markets if market.name == origin_name), None
        )
        if active_tab == str(port_view):
            port_view.render(origin_name, origin)
        elif active_tab == str(cargo_view):
            cargo_view.render(
                origin_name, origin, markets, readable_markets, planning_player
            )

    def update_loop():
        refresh_market_data()
        root.after(5000, update_loop)

    print("=== Island Market Scanner ===")

    try:
        process_name = "Sailwind.exe"
        pm = open_read_only_process(process_name)
    except pymem.exception.ProcessNotFound:
        print(
            f"Error: {process_name} is not running. Please start the game and try again."
        )
        return 1
    except pymem.exception.CouldNotOpenProcess:
        print(f"Error: Could not open {process_name} for read-only access.")
        return 1

    # Set AppUserModelID for taskbar icon on Windows
    myappid = "mycompany.myproduct.subproduct.version"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    root = tk.Tk()
    root.title("Sailwind Market Scanner")
    root.geometry("1050x680")
    root.minsize(890, 460)

    icon = Image.open(APP_DIR / "boat.ico")
    icon = ImageTk.PhotoImage(icon)
    root.iconphoto(True, icon)

    configure_theme(root)

    def budget():
        return player.principal if automatic_balance is None else automatic_balance

    def update_player_summary():
        cash_label = "Saved cash" if automatic_balance is not None else "Cash"
        player_summary.config(
            text=(
                f"{cash_label} {budget():,.8g} {player.currency}  ·  "
                f"Weight {player.mass_limit:,.8g}  ·  Volume {player.volume_limit:,.8g}"
            )
        )

    root.grid_rowconfigure(2, weight=1)
    root.grid_columnconfigure(0, weight=1)

    button_frame = ttk.Frame(root, padding=(14, 10))
    button_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 0))

    player = Player()
    print(player)
    markets = []
    start_button = ttk.Button(
        button_frame,
        text="Initialize Markets",
        style="Accent.TButton",
        command=find_markets,
    )
    start_button.grid(row=0, column=0, sticky="w", padx=(0, 6))
    create_tooltip(
        start_button,
        "Find markets once per game session. Stock and price estimates update automatically afterward.",
    )

    status_label = ttk.Label(
        button_frame, text="Initialize markets to begin.", style="Muted.TLabel"
    )
    status_label.grid(row=1, column=0, columnspan=5, sticky="w", pady=(7, 0))
    refresh_status = ttk.Label(button_frame, text="", style="Muted.TLabel")
    refresh_status.grid(row=2, column=0, columnspan=5, sticky="w", pady=(3, 0))
    player_summary = ttk.Label(button_frame, style="Muted.TLabel")
    player_summary.grid(row=1, column=5, rowspan=2, sticky="e", pady=(7, 0))
    button_frame.columnconfigure(5, weight=1)
    update_player_summary()

    diagnostics_button = ttk.Menubutton(button_frame, text="Diagnostics")
    diagnostics_menu = tk.Menu(diagnostics_button, tearoff=False)
    diagnostics_menu.add_command(label="Copy diagnostics", command=copy_diagnostics)
    diagnostics_button.configure(menu=diagnostics_menu)
    diagnostics_button.grid(row=0, column=4, padx=(8, 0))
    create_tooltip(diagnostics_button, "Options for troubleshooting market reads.")

    ttk.Label(button_frame, text="Departure port").grid(row=0, column=1, padx=(12, 4))
    origin_port_var = tk.StringVar(value=START_GROUPS_OPTION)
    origin_port_picker = ttk.Combobox(
        button_frame, textvariable=origin_port_var, width=24, state="disabled"
    )
    origin_port_picker.grid(row=0, column=2, sticky="w")
    origin_port_picker.bind("<<ComboboxSelected>>", lambda event: update_chart())
    create_tooltip(
        origin_port_picker,
        "Choose a port for Port Market and departures. Selected start groups restores regional browsing.",
    )

    player_frame = ttk.Frame(root, padding=(14, 10))
    player_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 0))
    player_frame.grid_remove()
    settings_button = ttk.Button(
        button_frame,
        text="Settings",
        command=lambda: toggle_panel(player_frame, settings_button, "Settings"),
    )
    settings_button.grid(row=0, column=3, padx=(12, 0))
    create_tooltip(
        settings_button, "Edit available cash, exchange rate, and cargo limits."
    )

    player_fields = (
        ("principal", "Player Principal:", "Available money in the selected currency."),
        (
            "conversion_rate",
            "Per Gold Lion:",
            "How many coins of the selected currency the exchange quotes for one Gold Lion.",
        ),
        (
            "mass_limit",
            "Weight Limit:",
            "Maximum cargo weight.\nDhow ~1000, sanbuq ~4000.",
        ),
        (
            "volume_limit",
            "Volume Limit:",
            "Maximum cargo volume.\nDhow ~40, sanbuq ~120.",
        ),
    )
    player_vars = {}
    for column, (key, label, tooltip) in enumerate(player_fields, start=1):
        variable = tk.StringVar(value=getattr(player, key))
        player_vars[key] = variable
        field_label = ttk.Label(player_frame, text=label)
        field_label.grid(row=0, column=column, sticky="w", padx=(0, 12))
        create_tooltip(field_label, tooltip)
        entry = ttk.Entry(player_frame, textvariable=variable, width=15)
        entry.grid(row=1, column=column, sticky="ew", padx=(0, 12), pady=(4, 0))
        create_tooltip(entry, tooltip)
        if key == "conversion_rate":
            rate_entry = entry
        elif key == "principal":
            principal_entry = entry

    player_status = ttk.Label(player_frame, text="", style="Muted.TLabel")
    player_status.grid(row=2, column=0, columnspan=6, sticky="w")
    ttk.Label(player_frame, text="Currency:").grid(row=0, column=0, sticky="w")
    currency_var = tk.StringVar(value=player.currency)
    currency_picker = ttk.Combobox(
        player_frame,
        textvariable=currency_var,
        values=tuple(player.conversion_rates),
        state="readonly",
        width=17,
    )
    currency_picker.grid(row=1, column=0, sticky="ew", padx=(0, 12), pady=(4, 0))
    create_tooltip(
        currency_picker,
        "Select the currency used for market quotes. Check that Player Principal matches your balance in that currency.",
    )

    def show_currency_rate():
        player_vars["conversion_rate"].set(player.conversion_rate)
        rate_entry.configure(
            state="readonly" if player.currency == GOLD_CURRENCY else "normal"
        )

    def change_currency(_event):
        player.currency = currency_var.get()
        show_currency_rate()
        save_and_refresh(player_status)

    currency_picker.bind("<<ComboboxSelected>>", change_currency)
    show_currency_rate()
    auto_rate_var = tk.BooleanVar(value=player.auto_rates)

    def toggle_auto_rate():
        player.auto_rates = auto_rate_var.get()
        show_currency_rate()
        save_and_refresh(player_status)

    auto_rate_toggle = ttk.Checkbutton(
        player_frame,
        text="Use exchange rates from save",
        variable=auto_rate_var,
        command=toggle_auto_rate,
    )
    auto_rate_toggle.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
    create_tooltip(
        auto_rate_toggle,
        "Refresh rates after a save or autosave. Available when there is one Sailwind save slot.",
    )
    rate_source = ttk.Label(player_frame, style="Muted.TLabel")
    rate_source.grid(row=3, column=2, columnspan=4, sticky="w", pady=(4, 0))
    auto_balance_var = tk.BooleanVar(value=player.auto_balance)

    def toggle_auto_balance():
        player.auto_balance = auto_balance_var.get()
        save_and_refresh(player_status)

    auto_balance_toggle = ttk.Checkbutton(
        player_frame,
        text="Use cash balance from save",
        variable=auto_balance_var,
        command=toggle_auto_balance,
    )
    auto_balance_toggle.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))
    create_tooltip(
        auto_balance_toggle,
        "Use the selected currency's wallet balance after a save or autosave.",
    )
    balance_source = ttk.Label(player_frame, style="Muted.TLabel")
    balance_source.grid(row=4, column=2, columnspan=4, sticky="w", pady=(4, 0))
    update_button = ttk.Button(
        player_frame,
        text="Update Values",
        command=lambda: update_values(player_vars, player_status),
    )
    update_button.grid(row=1, column=5, sticky="w")

    tabs = ttk.Notebook(root)
    tabs.grid(row=2, column=0, sticky="nsew", padx=16, pady=(10, 0))
    version_label = ttk.Label(
        root, text=f"Version {APP_VERSION}", style="Footer.TLabel"
    )
    version_label.grid(row=3, column=0, sticky="e", padx=16, pady=(4, 8))
    routes_view = TradeRoutesView(tabs, player.min_profit, update_chart, update_values)
    port_view = PortMarketView(tabs)
    cargo_view = CargoPlanView(tabs, update_chart)
    tabs.add(routes_view, text="Trade Routes")
    tabs.add(port_view, text="Port Market")
    tabs.add(cargo_view, text="Cargo Plan")

    def tab_help(event):
        try:
            tab = tabs.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return None
        return {
            0: "Compare estimated profit for one product at a time across ports.",
            1: "See stock and estimated one-crate prices at the selected departure port.",
            2: "Suggest a mixed load for one destination within your cash and cargo limits.",
        }.get(tab)

    create_tooltip(tabs, tab_help)

    tabs.bind("<<NotebookTabChanged>>", lambda event: update_chart())
    root.after(2000, update_loop)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
