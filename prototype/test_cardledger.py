import unittest

from cardledger import compare_channels, grading_ev, load_config, net_proceeds


class NetProceedsTest(unittest.TestCase):
    def setUp(self):
        self.config = load_config()

    def test_worked_example_matches_design_doc(self):
        results = {b.channel: b for b in compare_channels(
            self.config, {"ebay_uk": 420, "ebay_us_eis": 560, "cardmarket_de": 495}, cost_basis=180)}
        self.assertAlmostEqual(results["ebay_uk"].net, 351.10, places=2)
        self.assertAlmostEqual(results["ebay_us_eis"].net, 343.10, places=2)
        self.assertAlmostEqual(results["cardmarket_de"].net, 370.60, places=2)

    def test_channels_ranked_by_net(self):
        results = compare_channels(self.config, {"ebay_uk": 420, "cardmarket_de": 495}, 180)
        self.assertEqual(results[0].channel, "cardmarket_de")

    def test_cheap_card_can_lose_money(self):
        self.assertLess(net_proceeds(self.config, "ebay_uk", 5, cost_basis=2).profit, 0)

    def test_grading_probabilities_must_sum_to_one(self):
        with self.assertRaises(ValueError):
            grading_ev(self.config, "ebay_uk", 25, [("10", 0.5, 140)], 22, 8)

    def test_grading_ev(self):
        result = grading_ev(self.config, "ebay_uk", 25,
                            [("10", 0.15, 140), ("9", 0.55, 60), ("8", 0.30, 30)], 22, 8)
        self.assertGreater(result["ev_of_grading"], 0)
        self.assertLess(result["worst_case_vs_raw"], 0)


if __name__ == "__main__":
    unittest.main()
