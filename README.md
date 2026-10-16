# CardLedger

A platform to help a Pokémon card reseller value cards against international markets and see real profit after every cost.

- **Solution design:** [docs/SOLUTION_DESIGN.md](docs/SOLUTION_DESIGN.md)
- **Prototype profit and channel calculator:** [prototype/](prototype/) (Python 3, standard library only)

```bash
cd prototype
python3 cardledger.py --cost 180 --price ebay_uk=420 --price ebay_us_eis=560 --price cardmarket_de=495
python3 -m unittest
```

Fee, FX and postage assumptions are in `prototype/fees.json`. They are indicative only, so check them against each platform's current fee page.
