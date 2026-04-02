from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # Parse the TradingView payload
        data = request.get_json(force=True)

        signal = data.get("signal", "UNKNOWN")
        close = data.get("close", "N/A")
        date = data.get("date", "N/A")
        ticker = data.get("ticker", "BTCUSD")
        flipped = data.get("flipped", False)

        # Color: green for LONG, red for SHORT
        color = 0x2ECC71 if signal == "LONG" else 0xE74C3C
        emoji = "🟢" if signal == "LONG" else "🔴"

        # Build Discord embed
        embed = {
            "title": f"{emoji}  {ticker} Daily Signal",
            "color": color,
            "fields": [
                {"name": "Signal", "value": f"**{signal}**", "inline": True},
                {"name": "Close", "value": f"${close:,.2f}" if isinstance(close, (int, float)) else str(close), "inline": True},
                {"name": "Date", "value": date, "inline": True},
            ],
            "footer": {"text": "TTS Variant A • Daily Close"},
        }

        # Build payload — ping @everyone on signal flip
        payload = {"embeds": [embed]}
        if flipped:
            payload["content"] = f"@everyone ⚡ Signal flipped to **{signal}**!"

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
