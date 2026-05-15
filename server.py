from flask import Flask, request
import requests
import os
import json
from threading import Lock
from datetime import datetime

app = Flask(__name__)
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
RATIOS_DISCORD_WEBHOOK_URL = os.environ.get("RATIOS_DISCORD_WEBHOOK_URL")
LEVERAGE = 5

# === In-memory store for ratio signals ===
# Collects all 3 ratio alerts before posting one consolidated message
ratio_buffer = {}
ratio_lock = Lock()
EXPECTED_RATIOS = {"ETHBTC", "SOLETH", "SOLBTC"}


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        signal = data.get("signal", "UNKNOWN")
        close = data.get("close", "N/A")
        date = data.get("date", "N/A")
        ticker = data.get("ticker", "BTCUSD")
        flipped = data.get("flipped", False)
        entry = data.get("entry", "N/A")
        pnl = data.get("pnl", 0)
        color = 0x2ECC71 if signal == "LONG" else 0xE74C3C
        emoji = "\U0001f7e2" if signal == "LONG" else "\U0001f534"
        if isinstance(pnl, (int, float)):
            leveraged_pnl = pnl * LEVERAGE
            pnl_str = f"{leveraged_pnl:+.2f}%"
        else:
            pnl_str = "N/A"
        close_str = f"${close:,.2f}" if isinstance(close, (int, float)) else str(close)
        entry_str = f"${entry:,.2f}" if isinstance(entry, (int, float)) else str(entry)
        embed = {
            "title": f"{emoji}  {ticker} Daily Signal",
            "color": color,
            "fields": [
                {"name": "Signal", "value": f"**{signal}**", "inline": True},
                {"name": "Close", "value": close_str, "inline": True},
                {"name": "Date", "value": date, "inline": True},
                {"name": "Entry Price", "value": entry_str, "inline": True},
                {"name": "P&L", "value": pnl_str, "inline": True},
            ],
            "footer": {"text": "TTS \u2022 Daily Close \u2022 20% allocation \u00b7 5x leverage"},
        }
        payload = {"embeds": [embed]}
        if flipped:
            payload["content"] = f"@everyone \u26a1 Signal flipped to **{signal}**!"
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        resp.raise_for_status()
        return "OK", 200
    except Exception as e:
        print(f"Error: {e}")
        return "Error", 500


@app.route("/ratios", methods=["POST"])
def ratios():
    try:
        data = request.get_json(force=True)
        ratio = data.get("ratio")
        signal = data.get("signal")
        date = data.get("date")

        if not ratio or not signal or not date:
            return "Missing fields", 400

        with ratio_lock:
            # Reset buffer if this is a new date
            if ratio_buffer.get("date") != date:
                ratio_buffer.clear()
                ratio_buffer["date"] = date
                ratio_buffer["signals"] = {}

            ratio_buffer["signals"][ratio] = signal

            # Only post once all 3 ratios have reported in
            if set(ratio_buffer["signals"].keys()) != EXPECTED_RATIOS:
                return "Buffered", 200

            signals = ratio_buffer["signals"].copy()
            ratio_buffer.clear()

        # Determine top asset (the one that's long against the other two)
        # ETHBTC long = ETH > BTC, SOLETH long = SOL > ETH, SOLBTC long = SOL > BTC
        scores = {"ETH": 0, "BTC": 0, "SOL": 0}
        if signals["ETHBTC"] == "LONG":
            scores["ETH"] += 1
        else:
            scores["BTC"] += 1
        if signals["SOLETH"] == "LONG":
            scores["SOL"] += 1
        else:
            scores["ETH"] += 1
        if signals["SOLBTC"] == "LONG":
            scores["SOL"] += 1
        else:
            scores["BTC"] += 1
        top_asset = max(scores, key=scores.get)

        # Format date nicely (2026-5-15 -> MAY 15 2026)
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            date_pretty = dt.strftime("%b %d %Y").upper()
        except Exception:
            date_pretty = date.upper()

        def fmt(name):
            sig = signals[name]
            emoji = "\U0001f7e2" if sig == "LONG" else "\U0001f534"
            return f"{emoji} **{name}** — {sig}"

        description = (
            f"**TOP ASSET: {top_asset}**\n\n"
            f"{fmt('ETHBTC')}\n"
            f"{fmt('SOLETH')}\n"
            f"{fmt('SOLBTC')}"
        )

        embed = {
            "title": f"RATIO ANALYSIS — {date_pretty}",
            "description": description,
            "color": 0x3498DB,
            "footer": {"text": "Treeline Ratios \u2022 Daily Close"},
        }

        resp = requests.post(RATIOS_DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
        resp.raise_for_status()
        return "Posted", 200

    except Exception as e:
        print(f"Ratios error: {e}")
        return "Error", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
