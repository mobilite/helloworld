import unittest

from cardledger import compare_channels, grading_ev, load_config, net_proceeds


class NetProceedsTest(unittest.TestCase):
    def setUp(self):
        self.config = load_config()

    def test_worked_example_matches_design_doc(self):
        results = {b.channel: b for b in compare_channels(
            self.config, {"trademe_nz": 850, "ebay_au": 820, "ebay_us": 560}, cost_basis=380)}
        self.assertAlmostEqual(results["trademe_nz"].net, 748.77, places=2)
        self.assertAlmostEqual(results["ebay_au"].net, 720.73, places=2)
        self.assertAlmostEqual(results["ebay_us"].net, 747.48, places=2)

    def test_channels_ranked_by_net(self):
        results = compare_channels(self.config, {"trademe_nz": 850, "ebay_au": 820}, 380)
        self.assertEqual(results[0].channel, "trademe_nz")

    def test_trade_me_success_fee_is_capped(self):
        self.assertEqual(net_proceeds(self.config, "trademe_nz", 5000).final_value_fee, 249.0)

    def test_cheap_card_loses_money_overseas_but_not_locally(self):
        self.assertLess(net_proceeds(self.config, "ebay_us", 15, cost_basis=5).profit, 0)
        self.assertGreater(net_proceeds(self.config, "trademe_nz", 25, cost_basis=5).profit, 0)

    def test_grading_probabilities_must_sum_to_one(self):
        with self.assertRaises(ValueError):
            grading_ev(self.config, "ebay_us", 40, [("10", 0.5, 240)], 45, 35)

    def test_grading_ev(self):
        result = grading_ev(self.config, "ebay_us", 40,
                            [("10", 0.15, 240), ("9", 0.55, 100), ("8", 0.30, 55)], 45, 35)
        self.assertLess(result["worst_case_vs_raw"], 0)


if __name__ == "__main__":
    unittest.main()
