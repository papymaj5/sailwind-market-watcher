import re
import struct
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import market
from memhack import open_read_only_process
from save_economy import SavedGameEconomy, SaveEconomy, read_save_economy
from settings import (
    DEFAULT_CURRENCY,
    GOLD_CURRENCY,
    PLAYER_SETTINGS,
    Player,
    load_player_settings,
    save_player_settings,
)


class PricingTests(unittest.TestCase):
    def product(self, supply, limit=10):
        with patch("market.read_game_memory", return_value=supply):
            product = market.Product("Goods", 0, None, limit)
            product.update_product(34.22)
        return product

    def test_stock_and_prices_for_synthetic_goods_supply(self):
        # Supply 30 and limit 10 are synthetic inputs, not a captured 0.41 market.
        goods = self.product(30)
        self.assertEqual(goods.amnt, 21)
        self.assertEqual(goods.calculate_buy_mult(1), 193)
        self.assertEqual(goods.calculate_sell_mult(1), 188)

    def test_unavailable_stock_cannot_be_purchased(self):
        goods = self.product(5)
        self.assertEqual(goods.amnt, 0)
        self.assertEqual(goods.max_quantity(SimpleNamespace(principal=10000)), 0)

    def test_departure_and_destination_filters(self):
        origin = SimpleNamespace(name="Gold Rock City", products=[self.product(30)])
        other = SimpleNamespace(name="Oasis", products=[self.product(30)])
        destination = SimpleNamespace(name="Neverdin", products=[self.product(0)])
        player = SimpleNamespace(
            principal=1300, min_profit=0, mass_limit=4000, volume_limit=120
        )
        group = market.IslandGroups.get_group(destination.name)
        markets = [origin, other, destination]
        routes = market.generate_trade_routes([], [group], player, markets, origin.name)
        self.assertEqual(
            [(route["Start Market"], route["End Market"]) for route in routes],
            [(origin.name, destination.name)],
        )
        self.assertEqual(
            market.generate_trade_routes([], [], player, markets, origin.name), []
        )


class CargoPlanTests(unittest.TestCase):
    def test_mixed_load_reprices_each_crate_and_respects_limits(self):
        def source(name, stock):
            return SimpleNamespace(
                name=name,
                amnt=stock,
                supply=20,
                weight=2,
                volume=1,
                calc_buy_price=lambda supply: 10 + (20 - supply),
            )

        def destination(name, starting_price):
            return SimpleNamespace(
                name=name,
                supply=0,
                calc_sell_price=lambda supply: starting_price - 5 * supply,
            )

        origin = SimpleNamespace(
            products=[source("Goods", 10), source("Pork", 1), source("Books", 0)]
        )
        target = SimpleNamespace(
            products=[
                destination("Goods", 25),
                destination("Pork", 23),
                destination("Books", 100),
            ]
        )
        player = SimpleNamespace(principal=31, mass_limit=6, volume_limit=3)
        lines = market.plan_cargo(origin, target, player)
        self.assertEqual(
            [(line.product, line.quantity, line.buy, line.sell) for line in lines],
            [("Goods", 2, 21, 45), ("Pork", 1, 10, 23)],
        )
        self.assertEqual(sum(line.weight for line in lines), player.mass_limit)
        self.assertEqual(sum(line.volume for line in lines), player.volume_limit)
        self.assertEqual(sum(line.buy for line in lines), player.principal)

    def test_plan_stops_when_destination_price_no_longer_covers_cost(self):
        origin = SimpleNamespace(
            products=[
                SimpleNamespace(
                    name="Goods",
                    amnt=10,
                    supply=20,
                    weight=1,
                    volume=1,
                    calc_buy_price=lambda _: 10,
                )
            ]
        )
        target = SimpleNamespace(
            products=[
                SimpleNamespace(
                    name="Goods",
                    supply=0,
                    calc_sell_price=lambda supply: 12 - 2 * supply,
                )
            ]
        )
        player = SimpleNamespace(principal=100, mass_limit=100, volume_limit=100)
        self.assertEqual(
            [line.quantity for line in market.plan_cargo(origin, target, player)], [1]
        )


class ScannerTests(unittest.TestCase):
    def test_game_handle_requests_only_query_and_read_access(self):
        with (
            patch(
                "memhack.pymem.process.process_from_name",
                return_value=SimpleNamespace(th32ProcessID=123),
            ) as find,
            patch("memhack.pymem.process.open", return_value=456) as open_process,
        ):
            reader = open_read_only_process("Sailwind.exe")

        find.assert_called_once_with("Sailwind.exe", exact_match=True)
        access = market.pymem.ressources.structure.PROCESS
        open_process.assert_called_once_with(
            123,
            debug=False,
            process_access=access.PROCESS_QUERY_INFORMATION.value
            | access.PROCESS_VM_READ.value,
        )
        self.assertEqual(reader.process_handle, 456)

    def test_refresh_reports_bad_markets_and_retries_them(self):
        from unittest.mock import Mock

        healthy = SimpleNamespace(name="Gold Rock City", update_products=Mock())
        flaky = SimpleNamespace(
            name="Neverdin",
            update_products=Mock(side_effect=[ValueError("Invalid stock"), None]),
        )
        readable, errors = market.refresh_markets([healthy, flaky], 34.22)
        self.assertEqual(readable, [healthy])
        self.assertEqual(errors, ["Neverdin: Invalid stock"])

        readable, errors = market.refresh_markets([healthy, flaky], 34.22)
        self.assertEqual(readable, [healthy, flaky])
        self.assertEqual(errors, [])

    def test_placeholder_slots_are_skipped_without_shifting_products(self):
        pm = SimpleNamespace(read_longlong=lambda address: 100)
        scanned_market = SimpleNamespace(pm=pm, base=0, limit=10, index=0)
        with patch("market.read_game_memory", return_value=30):
            products = market.Market._init_products(scanned_market)

        names = market.Products.NAMES
        self.assertNotIn("---", [product.name for product in products])
        self.assertNotIn("---2", [product.name for product in products])
        for product in products:
            self.assertEqual(
                product.supply_address, 100 + 0x24 + names.index(product.name) * 4
            )
        self.assertEqual(names[61:], ["Coffee", "Salt", "Saffron"])

    def test_exclusive_products_can_only_be_purchased_at_their_origin(self):
        pm = SimpleNamespace(read_longlong=lambda address: 100)
        for index in (0, 21, 22, 25, 33):
            with (
                self.subTest(port=index),
                patch("market.read_game_memory", return_value=30),
            ):
                scanned_market = SimpleNamespace(pm=pm, base=0, limit=10, index=index)
                products = {
                    product.name: product
                    for product in market.Market._init_products(scanned_market)
                }
                for (
                    name,
                    allowed_port,
                ) in market.Products.EXCLUSIVE_PURCHASE_PORTS.items():
                    self.assertEqual(
                        products[name].amnt, 21 if index == allowed_port else 0
                    )
                    self.assertGreater(products[name].sell_price, 0)
                self.assertEqual(products["Coffee"].amnt, 21)

    def test_anchored_search_matches_original_signature(self):
        signature = rb"..\x00\x00\x80\x3F\x00\x00.\x42.\x00\x00\x00\x6F\x12\x83\x3A\x00\x00\x80\x3F"
        match_bytes = b"\n\0\0\0\x80\x3f\0\0\n\x42\0\0\0\0\x6f\x12\x83\x3a\0\0\x80\x3f"
        data = match_bytes * 2 + match_bytes[:-1] + b"\0" + match_bytes
        memory = market.pymem.ressources.structure
        limit = 0x7FFFFFFF0000 if sys.maxsize > 2**32 else 0x7FFF0000
        regions = [
            SimpleNamespace(
                BaseAddress=0,
                RegionSize=len(data),
                state=memory.MEMORY_STATE.MEM_COMMIT,
                protect=memory.MEMORY_PROTECTION.PAGE_READWRITE,
            ),
            SimpleNamespace(
                BaseAddress=len(data), RegionSize=limit - len(data), state=0, protect=0
            ),
        ]
        with (
            patch("market.pymem.memory.virtual_query", side_effect=regions),
            patch("market.pymem.memory.read_bytes", return_value=data) as read,
        ):
            result = market.scan_market_addresses(None)
        self.assertEqual(
            result.addresses,
            [m.start() for m in re.finditer(signature, data, re.DOTALL)],
        )
        self.assertEqual(len(result.addresses), 3)
        read.assert_called_once_with(None, 0, len(data))


class SavedGameEconomyTests(unittest.TestCase):
    def save_data(self, lions=0.21465273201465607, balance=1298):
        return (
            struct.pack("<Biiii", 0, 1, -1, 1, 0)
            + struct.pack("<Bi", 12, 2)
            + b"\x0fAssembly-CSharp"
            + struct.pack("<Bi", 5, 1)
            + b"\x0dSaveContainer"
            + struct.pack("<i", 3)
            + b"\x0fcurrentCurrency\x0eplayerCurrency\x0dcurrencyRates\x00\x07\x07\x08\x08\x0b"
            + struct.pack("<iiBiBi", 2, 0, 9, 12, 9, 13)
            + struct.pack("<BiiB4i", 15, 12, 4, 8, balance, 15, 23, 0)
            + struct.pack(
                "<BiiB4f", 15, 13, 4, 11, lions, 1.89633727, 0.49189484, 0.00585
            )
        )

    def test_reads_exchange_quote_and_rejects_incomplete_save(self):
        data = self.save_data()
        economy = read_save_economy(data)
        self.assertEqual(economy.rates["Al'Ankh Lions"], 36.32585)
        self.assertEqual(
            economy.balances,
            {
                "Al'Ankh Lions": 1298,
                "Emerald Dragons": 15,
                "Aestrin Crowns": 23,
                "Gold Lions": 0,
            },
        )
        with self.assertRaises(ValueError):
            read_save_economy(data[:-1])

    def test_refreshes_after_save_changes_and_avoids_ambiguous_slots(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            save = root / "slot0.save"
            source = SavedGameEconomy(root)
            save.write_bytes(self.save_data())
            self.assertEqual(source.read()[0].rates["Al'Ankh Lions"], 36.32585)
            save.write_bytes(self.save_data(lions=0.2, balance=500) + b"\x0b")
            economy, _ = source.read()
            self.assertNotEqual(economy.rates["Al'Ankh Lions"], 36.32585)
            self.assertEqual(economy.balances["Al'Ankh Lions"], 500)
            (root / "slot1.save").write_bytes(self.save_data())
            self.assertEqual(source.read(), (SaveEconomy(), "Multiple saves found."))


class SettingsTests(unittest.TestCase):
    def test_gold_lion_rate_is_fixed(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "player-settings.json"
            save_player_settings(
                path,
                {"currency": GOLD_CURRENCY, "conversion_rates": {GOLD_CURRENCY: 2}},
            )
            with patch("settings.PLAYER_SETTINGS_PATH", path):
                player = Player()
            self.assertEqual(player.currency, GOLD_CURRENCY)
            self.assertEqual(player.conversion_rate, 1)

    def test_currency_rates_and_selection_survive_restart(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "player-settings.json"
            save_player_settings(path, {"conversion_rate": 36.32585})
            with patch("settings.PLAYER_SETTINGS_PATH", path):
                player = Player()
                self.assertEqual(player.currency, DEFAULT_CURRENCY)
                self.assertEqual(player.conversion_rate, 36.32585)

                player.currency = "Aestrin Crowns"
                player.conversion_rates[player.currency] = 83.5
                save_player_settings(path, vars(player))
                restored = Player()
                self.assertEqual(restored.currency, "Aestrin Crowns")
                self.assertEqual(restored.conversion_rate, 83.5)
                restored.currency = DEFAULT_CURRENCY
                self.assertEqual(restored.conversion_rate, 36.32585)

    def test_saved_settings_round_trip_and_corrupt_file_fallback(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "watcher" / "player-settings.json"
            self.assertEqual(load_player_settings(path), PLAYER_SETTINGS)
            saved = {**PLAYER_SETTINGS, "mass_limit": 1000, "volume_limit": 40}
            save_player_settings(path, saved)
            self.assertEqual(load_player_settings(path), saved)
            path.write_text("{", encoding="utf-8")
            self.assertEqual(load_player_settings(path), PLAYER_SETTINGS)
