"""CardLedger prototype: net-profit and channel comparison for a single card.

Turns a market price on each channel into the money that actually lands in
the seller's account, then ranks channels by profit. Fee assumptions live in
fees.json so they can be updated without touching code.

Usage:
    python cardledger.py --cost 180 --price ebay_uk=420 --price ebay_us_eis=560 \
        --price cardmarket_de=495
    python cardledger.py --cost 12 --price ebay_uk=25 --grade-fee 22 --grade-shipping 8 \
        --graded "10:0.15:140" --graded "9:0.55:60" --graded "8:0.30:30"
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).with_name("fees.json")


@dataclass
class Breakdown:
    channel: str
    label: str
    gross_home: float
    final_value_fee: float
    fixed_fees: float
    payment_fee: float
    fx_spread: float
    postage: float
    packaging: float
    returns_allowance: float
    net: float
    cost_basis: float

    @property
    def profit(self) -> float:
        return self.net - self.cost_basis

    @property
    def margin(self) -> float:
        return self.profit / self.gross_home if self.gross_home else 0.0

    @property
    def roi(self) -> float:
        return self.profit / self.cost_basis if self.cost_basis else float("inf")


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    return json.loads(path.read_text())


def net_proceeds(config: dict, channel: str, price_local: float,
                 postage_charged_local: float = 0.0, cost_basis: float = 0.0) -> Breakdown:
    """Net amount (home currency) from selling at `price_local` on `channel`."""
    ch = config["channels"][channel]
    rate = config["fx_to_home"][ch["currency"]]
    # eBay-style fees apply to the total the buyer pays, including postage.
    gross = (price_local + postage_charged_local) * rate

    fvf = gross * ch["final_value_pct"]
    fixed = ch["fixed_fee"] * rate if ch["currency"] != config["home_currency"] else ch["fixed_fee"]
    payment = gross * ch["payment_pct"] + ch["payment_fixed"] * rate
    fx_spread = gross * ch["fx_spread_pct"]
    postage = ch["postage_cost"]
    packaging = config["packaging_cost"]
    returns = gross * config["returns_allowance_pct"]

    net = gross - fvf - fixed - payment - fx_spread - postage - packaging - returns
    return Breakdown(channel, ch["label"], round(gross, 2), round(fvf, 2), round(fixed, 2),
                     round(payment, 2), round(fx_spread, 2), postage, packaging,
                     round(returns, 2), round(net, 2), cost_basis)


def compare_channels(config: dict, prices: dict[str, float], cost_basis: float) -> list[Breakdown]:
    results = [net_proceeds(config, ch, p, cost_basis=cost_basis) for ch, p in prices.items()]
    return sorted(results, key=lambda b: b.net, reverse=True)


def grading_ev(config: dict, channel: str, raw_price_local: float,
               graded_outcomes: list[tuple[str, float, float]],
               grade_fee: float, grade_shipping: float) -> dict:
    """Expected gain from grading versus selling raw on the same channel.

    graded_outcomes: (grade label, probability, local price at that grade).
    """
    total_p = sum(p for _, p, _ in graded_outcomes)
    if abs(total_p - 1.0) > 0.01:
        raise ValueError(f"grade probabilities must sum to 1 (got {total_p:.2f})")

    raw_net = net_proceeds(config, channel, raw_price_local).net
    grading_cost = grade_fee + grade_shipping
    per_grade = {g: net_proceeds(config, channel, price).net - grading_cost
                 for g, _, price in graded_outcomes}
    expected = sum(p * per_grade[g] for g, p, _ in graded_outcomes)
    return {
        "raw_net": raw_net,
        "expected_graded_net": round(expected, 2),
        "ev_of_grading": round(expected - raw_net, 2),
        "worst_case_vs_raw": round(min(per_grade.values()) - raw_net, 2),
        "grading_cost": grading_cost,
        "per_grade_net": {g: round(v, 2) for g, v in per_grade.items()},
    }


def grading_verdict(result: dict) -> str:
    """Require the expected gain to be worth the risk and the cash tied up."""
    ev = result["ev_of_grading"]
    if ev <= 0:
        return "SELL RAW"
    if ev < 0.5 * result["grading_cost"]:
        return "MARGINAL - grade only if confident in condition"
    return "GRADE"


def _print_comparison(results: list[Breakdown], currency: str) -> None:
    rows = [
        ("Gross", "gross_home"), ("Final value fee", "final_value_fee"),
        ("Fixed fees", "fixed_fees"), ("Payment fee", "payment_fee"),
        ("FX spread", "fx_spread"), ("Postage", "postage"), ("Packaging", "packaging"),
        ("Returns allowance", "returns_allowance"), ("NET PROCEEDS", "net"),
        ("Cost basis", "cost_basis"),
    ]
    width = 30
    print(f"{'(' + currency + ')':<20}" + "".join(f"{r.label:>{width}}" for r in results))
    for name, attr in rows:
        sign = "" if attr in ("gross_home", "net") else "-"
        print(f"{name:<20}" + "".join(f"{sign + format(getattr(r, attr), '.2f'):>{width}}" for r in results))
    print(f"{'PROFIT':<20}" + "".join(f"{r.profit:>{width}.2f}" for r in results))
    print(f"{'Margin':<20}" + "".join(f"{r.margin:>{width}.1%}" for r in results))
    print(f"{'ROI':<20}" + "".join(f"{r.roi:>{width}.1%}" for r in results))
    print(f"\nBest channel: {results[0].label} (net {results[0].net:.2f}, profit {results[0].profit:.2f})")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cost", type=float, required=True, help="cost basis in home currency")
    parser.add_argument("--price", action="append", required=True, metavar="CHANNEL=PRICE",
                        help="market price in the channel's own currency (repeatable)")
    parser.add_argument("--graded", action="append", default=[], metavar="GRADE:PROB:PRICE",
                        help="graded outcome on the first --price channel (repeatable)")
    parser.add_argument("--grade-fee", type=float, default=0.0)
    parser.add_argument("--grade-shipping", type=float, default=0.0)
    args = parser.parse_args(argv)

    config = load_config(args.config)
    prices = {}
    for item in args.price:
        channel, value = item.split("=")
        prices[channel] = float(value)

    _print_comparison(compare_channels(config, prices, args.cost), config["home_currency"])

    if args.graded:
        outcomes = [(g, float(p), float(v)) for g, p, v in (s.split(":") for s in args.graded)]
        first_channel = next(iter(prices))
        result = grading_ev(config, first_channel, prices[first_channel], outcomes,
                            args.grade_fee, args.grade_shipping)
        print(f"\nGrading on {config['channels'][first_channel]['label']}:")
        print(f"  Sell raw, net:            {result['raw_net']:.2f}")
        print(f"  Grade, expected net:      {result['expected_graded_net']:.2f}")
        print(f"  EV of grading:            {result['ev_of_grading']:+.2f}")
        print(f"  Worst case vs raw:        {result['worst_case_vs_raw']:+.2f}")
        print("  Verdict:", grading_verdict(result))


if __name__ == "__main__":
    main()
