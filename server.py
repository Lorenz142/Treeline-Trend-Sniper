from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

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

        # Color: green for LONG, red for SHORT
        color = 0x2ECC71 if signal == "LONG" else 0xE74C3C
        emoji = "\U0001f7e2" if signal == "LONG" else "\U0001f534"

      # P&L formatting
        if isinstance(pnl, (int, float)):
            pnl_str = f"{pnl:+.2f}%"
        else:
            pnl_str = "N/A"

        # Format prices
        close_str = f"${close:,.2f}" if isinstance(close, (int, float)) else str(close)
        entry_str = f"${entry:,.2f}" if isinstance(entry, (int, float)) else str(entry)

        # Build Discord embed
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
            "footer": {"text": "TTS Variant A \u2022 Daily Close"},
        }

        # Build payload — ping @everyone on signal flip
        payload = {"embeds": [embed]}
        if flipped:
            payload["content"] = f"@everyone \u26a1 Signal flipped to **{signal}**!"

        # Send to Discord
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        resp.raise_for_status()

        return "OK", 200

    except Exception as e:
        print(f"Error: {e}")
        return "Error", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
