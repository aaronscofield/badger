"""Host-side tests for the Yankees badge app's date and lookup flow."""

import builtins
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


APP = Path(__file__).resolve().parents[1] / "badge/apps/yankees_scores/__init__.py"
DATE = "2024-08-07"


def game(number, status, away=None, home=None, phase="Final"):
    return {
        "gameNumber": number,
        "status": {"detailedState": status, "abstractGameState": phase},
        "teams": {
            "away": {"team": {"abbreviation": "LAA"}, "score": away},
            "home": {"team": {"abbreviation": "NYY"}, "score": home},
        },
    }


class YankeesScoresTests(unittest.TestCase):
    def setUp(self):
        self.response = Mock(status_code=200)
        self.requests = Mock()
        self.requests.get.return_value = self.response
        self.network = Mock()
        self.network.WLAN.return_value.ifconfig.return_value = ("192.0.2.1",)
        self.modules = {
            "os": Mock(),
            "sys": SimpleNamespace(path=[]),
            "time": SimpleNamespace(localtime=lambda: (2026, 8, 7)),
            "network": self.network,
            "secrets": SimpleNamespace(WIFI_SSID="test", WIFI_PASSWORD=""),
            "requests": self.requests,
        }
        screen = Mock(width=320, height=240)
        screen.measure_text.return_value = (20, 8)
        self.screen = screen
        self.badge = Mock()
        self.app = {
            "__builtins__": dict(vars(builtins), __import__=self.import_module),
            "badge": self.badge, "screen": screen, "image": Mock(),
            "font": Mock(), "color": Mock(), "run": Mock(),
            "HIRES": 1, "VSYNC": 2,
        }
        self.app.update({"BUTTON_" + name: name for name in
                         ("LEFT", "RIGHT", "UP", "DOWN", "SELECT", "BACK")})
        exec(compile(APP.read_text(), str(APP), "exec"), self.app)

    def import_module(self, name, *args):
        if name in self.modules:
            return self.modules[name]
        raise ImportError(name)

    def frame(self, button=None):
        self.badge.pressed.side_effect = lambda name: name == button
        self.app["update"]()

    def lookup(self, games):
        self.app["date"] = [2024, 8, 7]
        self.response.json.return_value = {"dates": [{"date": DATE, "games": games}] if games else []}
        self.frame("SELECT")
        self.frame()

    def test_editing_leap_day_and_short_month(self):
        self.app["date"] = [2024, 2, 29]
        self.frame("UP")
        self.assertEqual(self.app["date"], [2025, 2, 28])
        self.app["date"] = [2025, 3, 31]
        self.frame("RIGHT")
        self.frame("UP")
        self.assertEqual(self.app["date"], [2025, 4, 30])

    def test_doubleheader_sorts_and_pages_between_scores(self):
        self.lookup([game(2, "Final", 8, 2), game(1, "Final", 0, 5)])
        self.assertEqual(self.app["games"], [
            (1, "Final", [("LAA", "0"), ("NYY", "5")]),
            (2, "Final", [("LAA", "8"), ("NYY", "2")]),
        ])
        self.assertIn("teamId=147&date=" + DATE, self.requests.get.call_args.args[0])
        self.frame("RIGHT")
        self.assertEqual(self.app["game_index"], 1)
        self.frame("BACK")
        self.assertEqual(self.app["page"], "date")
        self.assertEqual(self.app["date_key"](), DATE)

    def test_no_game_is_distinct_from_scheduled_and_postponed(self):
        self.lookup([])
        self.assertTrue(any("No Yankees game" in args.args[0]
                            for args in self.screen.text.call_args_list))
        self.frame("BACK")
        self.lookup([game(1, "Scheduled", 0, 0, "Preview"), game(2, "Postponed")])
        self.assertEqual(self.app["games"], [
            (1, "Scheduled", [("LAA", "-"), ("NYY", "-")]),
            (2, "Postponed", [("LAA", "-"), ("NYY", "-")]),
        ])

    def test_http_failure_closes_response_and_select_retries(self):
        self.response.status_code = 503
        with patch("builtins.print"):
            self.lookup([game(1, "Final", 1, 2)])
        self.assertEqual(self.app["page"], "error")
        self.response.close.assert_called_once()
        self.response.status_code = 200
        self.frame("SELECT")
        self.frame()
        self.assertEqual(self.app["page"], "results")
        self.assertEqual(self.response.close.call_count, 2)

    def test_wifi_timeout_never_calls_mlb(self):
        wlan = self.network.WLAN.return_value
        wlan.ifconfig.return_value = ("0.0.0.0",)
        clock = self.modules["time"]
        clock.ticks_ms = Mock(side_effect=(0, 12000))
        clock.ticks_add = lambda a, b: a + b
        clock.ticks_diff = lambda a, b: a - b
        self.frame("SELECT")
        self.assertEqual(self.app["page"], "wifi")
        self.frame()
        self.assertEqual(self.app["error"], "Wi-Fi timed out")
        self.requests.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
