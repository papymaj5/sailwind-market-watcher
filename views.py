"""Tk views for trade routes, port stock, and mixed cargo plans."""

import tkinter as tk
from tkinter import ttk

from market import generate_trade_routes, plan_cargo


def create_tooltip(widget, text):
    """Show fixed help or look up help for the area under the pointer."""
    window = None
    visible_text = None

    def hide_tip(_event=None):
        nonlocal window, visible_text
        if window is not None:
            window.destroy()
            window = None
        visible_text = None

    def show_tip(event):
        nonlocal window, visible_text
        message = text(event) if callable(text) else text
        if message == visible_text:
            return
        hide_tip()
        if message is None:
            return
        visible_text = message
        window = tk.Toplevel(widget)
        window.wm_overrideredirect(True)
        ttk.Label(
            window, text=message, style="Tooltip.TLabel", padding=8, wraplength=300
        ).pack()
        window.update_idletasks()
        x = min(event.x_root + 16, widget.winfo_screenwidth() - window.winfo_reqwidth())
        y = event.y_root + 20
        if y + window.winfo_reqheight() > widget.winfo_screenheight():
            y = event.y_root - window.winfo_reqheight() - 8
        window.wm_geometry(f"{x:+d}{y:+d}")

    widget.bind("<Enter>", show_tip, add="+")
    widget.bind("<Leave>", hide_tip, add="+")
    if callable(text):
        widget.bind("<Motion>", show_tip, add="+")


def add_heading_tooltips(table, help_by_column):
    def heading_help(event):
        if table.identify_region(event.x, event.y) != "heading":
            return None
        column = table.column(table.identify_column(event.x), "id")
        return help_by_column.get(column)

    create_tooltip(table, heading_help)


def toggle_panel(panel, button, label):
    if panel.winfo_manager():
        panel.grid_remove()
        button.config(text=label)
    else:
        panel.grid()
        button.config(text=f"Hide {label.lower()}")


def create_group_checkboxes(
    parent, names, default_func, label_text, tooltip, on_change
):
    """Creates a labeled group of checkboxes with default values."""
    label = ttk.Label(parent, text=label_text, style="Muted.TLabel")
    label.grid(row=0, column=0, columnspan=2, sticky="w", padx=3, pady=(0, 6))
    create_tooltip(label, tooltip)
    vars_dict = {name: tk.IntVar(value=default_func(name)) for name in names}
    half = (len(names) + 1) // 2
    for idx, (name, var) in enumerate(vars_dict.items()):
        ttk.Checkbutton(parent, text=name, variable=var, command=on_change).grid(
            row=(idx % half) + 1, column=idx // half, sticky="w", padx=10, pady=2
        )
    return vars_dict


def create_table(parent, row, headings, widths, left_aligned=(), minimum_widths=None):
    table = ttk.Treeview(parent, columns=tuple(headings), show="headings")
    add_heading_tooltips(table, headings)
    table.tag_configure("alternate", background="#142238")
    for column in headings:
        table.heading(column, text=column)
        options = {
            "width": widths[column],
            "anchor": "w" if column in left_aligned else "center",
        }
        if minimum_widths is not None:
            options["minwidth"] = minimum_widths[column]
        table.column(column, **options)

    table.grid(row=row, column=0, sticky="nsew")
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=table.yview)
    scrollbar.grid(row=row, column=1, sticky="ns")
    table.configure(yscrollcommand=scrollbar.set)

    def scroll(event):
        table.yview_scroll(-5 if event.delta > 0 else 5, "units")

    table.bind("<MouseWheel>", scroll)
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(row, weight=1)
    return table


def replace_rows(table, rows):
    table.delete(*table.get_children())
    for index, values in enumerate(rows):
        table.insert("", "end", tags=("alternate",) if index % 2 else (), values=values)


class TradeRoutesView(ttk.Frame):
    ISLAND_NAMES = (
        "Al'Ankh",
        "Aestrin",
        "Chronos",
        "Happy Bay",
        "Emerald Arch",
        "Fire Fish Lagoon",
    )
    ROUTE_KEYS = {
        "From": "Start Market",
        "To": "End Market",
        "Product": "Product",
        "Qnty": "Qnty",
        "$Buy": "$_Buy",
        "$Sell": "$_Sell",
        "$Profit": "$Profit",
        "$/Pound": "$/Pound",
        "$/Item": "$/Item",
    }

    def __init__(self, parent, min_profit, on_change, apply_settings):
        super().__init__(parent, style="Page.TFrame")
        self.on_change = on_change
        self.primary_column = "From"
        self.primary_reverse = False
        self.secondary_column = "$Profit"
        self.secondary_reverse = True

        filter_bar = ttk.Frame(self, padding=(8, 5))
        filter_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        filters = ttk.Frame(self, padding=(12, 8))
        filters.grid(row=1, column=0, columnspan=2, sticky="ew")
        filters.grid_remove()
        filters_button = ttk.Button(filter_bar, text="Filters")
        filters_button.configure(
            command=lambda: toggle_panel(filters, filters_button, "Filters")
        )
        filters_button.pack(side="left")
        create_tooltip(
            filters_button,
            "Choose island groups and the minimum profit for trade routes.",
        )

        self.start_group_frame = ttk.Frame(filters, padding=(0, 4))
        self.start_group_frame.grid(row=0, column=0, sticky="nw")
        end_group_frame = ttk.Frame(filters, padding=(0, 4))
        end_group_frame.grid(row=0, column=1, sticky="nw")
        self.start_groups = create_group_checkboxes(
            self.start_group_frame,
            self.ISLAND_NAMES,
            lambda name: name == "Al'Ankh",
            "Start Groups:",
            "Choose departure regions while Departure port is set to Selected start groups.",
            on_change,
        )
        self.end_groups = create_group_checkboxes(
            end_group_frame,
            self.ISLAND_NAMES,
            lambda name: True,
            "End Groups:",
            "Choose which regions can appear as destinations in Trade Routes.",
            on_change,
        )

        profit_frame = ttk.Frame(filters, padding=(14, 4))
        profit_frame.grid(row=0, column=2, sticky="nw")
        profit_status = ttk.Label(profit_frame, style="Muted.TLabel")
        profit_status.grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Label(profit_frame, text="Min Profit").grid(row=0, column=0, sticky="w")
        profit_var = tk.StringVar(value=min_profit)
        profit_entry = ttk.Entry(profit_frame, width=12, textvariable=profit_var)
        profit_entry.grid(row=1, column=0, sticky="w", padx=(0, 8))
        create_tooltip(
            profit_entry, "Only show routes above this estimated total profit."
        )
        ttk.Button(
            profit_frame,
            text="Apply",
            command=lambda: apply_settings({"min_profit": profit_var}, profit_status),
        ).grid(row=1, column=1)

        headings = {
            "From": "Port where you buy the cargo. Click to sort by departure port.",
            "To": "Port where you sell the cargo. Click to sort by destination.",
            "Product": "The commodity traded on this route.",
            "Qnty": "Planned crates / estimated crates available at the departure port.",
            "$Buy": "Estimated total purchase cost for the planned crates.",
            "$Sell": "Estimated total sale revenue for the planned crates.",
            "$Profit": "Estimated sale revenue minus purchase cost. Click to sort.",
            "$/Pound": "Estimated profit per pound of cargo. Click to sort.",
            "$/Item": "Estimated profit per crate. Click to sort.",
        }
        widths = dict(zip(headings, (155, 155, 105, 65, 75, 75, 80, 85, 75)))
        minimum_widths = {
            column: 55 if column.startswith("$") else 65 for column in headings
        }
        self.table = create_table(
            self, 2, headings, widths, ("From", "To", "Product"), minimum_widths
        )
        self.update_headings()

    def selected_groups(self, group_vars):
        return [
            f"{name} (Group {index})"
            for index, name in enumerate(self.ISLAND_NAMES, start=1)
            if group_vars[name].get()
        ]

    def render(self, origin_port, markets, player):
        if origin_port is None:
            self.start_group_frame.grid()
        else:
            self.start_group_frame.grid_remove()
        routes = generate_trade_routes(
            self.selected_groups(self.start_groups),
            self.selected_groups(self.end_groups),
            player,
            markets,
            origin_port,
        )
        # Stable sorts keep the selected profit metric ordered within each port.
        routes.sort(
            key=lambda route: route[self.secondary_column],
            reverse=self.secondary_reverse,
        )
        routes.sort(
            key=lambda route: route[self.ROUTE_KEYS[self.primary_column]],
            reverse=self.primary_reverse,
        )
        replace_rows(
            self.table,
            ([route[key] for key in self.ROUTE_KEYS.values()] for route in routes),
        )

    def sort_by(self, column):
        if column in ("From", "To"):
            self.primary_reverse = (
                not self.primary_reverse if column == self.primary_column else False
            )
            self.primary_column = column
        else:
            self.secondary_reverse = (
                not self.secondary_reverse if column == self.secondary_column else True
            )
            self.secondary_column = column
        self.update_headings()
        self.on_change()

    def update_headings(self):
        sortable = ("From", "To", "$Profit", "$/Pound", "$/Item")
        for column in sortable:
            arrow = ""
            if column == self.primary_column:
                arrow = " ▲" if self.primary_reverse else " ▼"
            elif column == self.secondary_column:
                arrow = " ⮟" if self.secondary_reverse else " ⮝"
            self.table.heading(
                column,
                text=column + arrow,
                command=lambda key=column: self.sort_by(key),
            )


class PortMarketView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=(8, 8, 8, 0))
        self.caption = ttk.Label(
            self, text="Initialize markets and select a departure port."
        )
        self.caption.grid(row=0, column=0, sticky="w", pady=(0, 8))
        headings = {
            "Product": "The commodity listed at the selected port.",
            "Stock": "Estimated number of crates available to buy at this port.",
            "Est. Buy / Crate": "Estimated cost of the next crate. A dash means there is no stock to buy.",
            "Est. Sell / Crate": "Estimated amount the port pays for one crate you already own.",
        }
        self.table = create_table(
            self, 1, headings, dict.fromkeys(headings, 150), ("Product",)
        )

    def render(self, origin_name, origin):
        if origin is None:
            message = (
                f"{origin_name} is currently unreadable."
                if origin_name
                else "Select a departure port to view its market."
            )
            self.caption.config(text=message)
            replace_rows(self.table, ())
            return

        self.caption.config(text=origin.name)
        products = sorted(origin.products, key=lambda product: product.name)
        replace_rows(
            self.table,
            (
                (
                    product.name,
                    product.amnt,
                    product.buy_price if product.amnt > 0 else "—",
                    product.sell_price,
                )
                for product in products
            ),
        )


class CargoPlanView(ttk.Frame):
    def __init__(self, parent, on_change):
        super().__init__(parent, padding=(8, 8, 8, 0))
        controls = ttk.Frame(self)
        controls.grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(controls, text="Destination").grid(row=0, column=0, padx=(0, 8))
        self.destination_var = tk.StringVar()
        self.destination_picker = ttk.Combobox(
            controls, textvariable=self.destination_var, state="disabled"
        )
        self.destination_picker.grid(row=0, column=1)
        self.destination_picker.bind("<<ComboboxSelected>>", lambda event: on_change())
        create_tooltip(
            self.destination_picker,
            "Choose the port where you plan to sell the entire load.",
        )
        self.summary = ttk.Label(
            self, text="Initialize markets and select a departure port."
        )
        self.summary.grid(row=1, column=0, sticky="w", pady=(0, 8))
        headings = {
            "Product": "The commodity included in the suggested load.",
            "Crates": "Number of crates to buy and sell.",
            "Est. Buy": "Total purchase cost using a separate estimate for each crate.",
            "Est. Sell": "Total sale revenue as each crate adds to destination stock.",
            "Est. Profit": "Estimated sale revenue minus purchase cost.",
            "Weight": "Total weight used by this commodity.",
            "Volume": "Total cargo space used by this commodity.",
        }
        self.table = create_table(
            self, 2, headings, dict.fromkeys(headings, 100), ("Product",)
        )

    def show_empty(self, message):
        replace_rows(self.table, ())
        self.summary.config(text=message)

    def render(self, origin_name, origin, markets, readable_markets, player):
        if origin is None:
            self.destination_var.set("")
            self.destination_picker.configure(values=(), state="disabled")
            message = (
                f"{origin_name} is currently unreadable."
                if origin_name
                else "Select a departure port to start a cargo plan."
            )
            self.show_empty(message)
            return

        destinations = {
            market.name: market
            for market in markets
            if market.name not in (origin.name, "Unknown Market")
        }
        self.destination_picker.configure(values=sorted(destinations), state="readonly")
        destination = destinations.get(self.destination_var.get())
        if destination is None:
            self.destination_var.set("")
            self.show_empty("Choose a destination for your cargo plan.")
            return
        if destination not in readable_markets:
            self.show_empty(f"{destination.name} is currently unreadable.")
            return

        lines = plan_cargo(origin, destination, player)
        if not lines:
            self.show_empty("No profitable cargo fits your current limits.")
            return

        replace_rows(
            self.table,
            (
                (
                    line.product,
                    line.quantity,
                    line.buy,
                    line.sell,
                    line.profit,
                    f"{line.weight:g}",
                    f"{line.volume:g}",
                )
                for line in sorted(lines, key=lambda item: item.product)
            ),
        )
        totals = {
            key: sum(getattr(line, key) for line in lines)
            for key in ("buy", "sell", "profit", "weight", "volume")
        }
        self.summary.config(
            text=(
                f"Est. profit {totals['profit']:,}   ·   Buy {totals['buy']:,}   ·   Sell {totals['sell']:,}"
                f"   ·   Weight {totals['weight']:g}/{player.mass_limit:g}"
                f"   ·   Volume {totals['volume']:g}/{player.volume_limit:g}"
            )
        )
