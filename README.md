# CardLedger

A platform to help a Pokémon card reseller in New Zealand value cards against international markets and see real profit after every cost.

- **Solution design:** [docs/SOLUTION_DESIGN.md](docs/SOLUTION_DESIGN.md)
- **Web calculator (phone or computer):** [web/calculator.html](web/calculator.html)
- **Prototype profit and channel calculator:** [prototype/](prototype/) (Python 3, standard library only)

```bash
cd prototype
python3 cardledger.py --cost 380 --price trademe_nz=850 --price ebay_au=820 --price ebay_us=560
python3 -m unittest
```

Fee, FX and NZ Post assumptions (in NZD) are in `prototype/fees.json`. They are indicative only, so check them against each platform's current fee page.
