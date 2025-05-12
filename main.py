import requests
import time
import os

# === CONFIGURATION ===
TELEGRAM_TOKEN = os.environ['7696841525:AAEZ0kLytesDTK0slQ1yP5I53TCgpX1fLd4']
TELEGRAM_CHAT_ID = os.environ['7736448938']
CHECK_INTERVAL = 300 # 5 minutes
THRESHOLDS = [{
    "percent": 15,
    "minutes": 60
}, {
    "percent": 10,
    "minutes": 30
}, {
    "percent": 25,
    "minutes": 120
}]

price_history = {}
alerted = set()


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print(f"Message Telegram envoyé : {message}")
        else:
            print(f"Erreur Telegram {response.status_code} : {response.text}")
    except Exception as e:
        print(f"Erreur lors de l'envoi Telegram : {str(e)}")


def get_bitget_prices():
    url = "https://api.bitget.com/api/spot/v1/market/tickers"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        print("Réponse Bitget (extrait) :",
              str(data)[:500]) # ligne pour debug temporaire
        if data.get("code") == "00000":
            return {
                coin["symbol"]: float(coin["close"])
                for coin in data["data"]
                if "close" in coin and coin.get("symbol", "").endswith("USDT")
            }
        return {}
    except Exception as e:
        print(f"Erreur API Bitget : {str(e)}")
        return {}


def check_price_changes(prices):
    now = time.time()
    for symbol, price in prices.items():
        if symbol not in price_history:
            price_history[symbol] = []
        price_history[symbol].append((now, price))

        max_minutes = max(t["minutes"] for t in THRESHOLDS)
        price_history[symbol] = [(t, p) for t, p in price_history[symbol]
                                 if now - t <= max_minutes * 60]

        for threshold in THRESHOLDS:
            delta = threshold["minutes"] * 60
            target_time = now - delta
            past_prices = [
                p for ts, p in price_history[symbol] if ts <= target_time
            ]

            if not past_prices:
                continue

            old_price = past_prices[-1]
            variation = ((price - old_price) / old_price) * 100

            if variation >= threshold["percent"] and (
                    symbol, threshold["minutes"]) not in alerted:
                message = (f"🚀 {symbol} a augmenté de {variation:.2f}% "
                           f"en {threshold['minutes']} minutes\n"
                           f"Prix actuel : {price:.8f}$")
                send_telegram_message(message)
                alerted.add((symbol, threshold["minutes"]))


def run_bot():
    print("Démarrage du bot de surveillance Bitget...")
    send_telegram_message("🤖 Bot de surveillance Bitget lancé")

    last_success = time.time()
    disconnect_notified = False

    while True:
        try:
            prices = get_bitget_prices()
            current_time = time.time()

            if len(prices) > 0:
                if disconnect_notified:
                    send_telegram_message("🟢 Bot reconnecté")
                    disconnect_notified = False
                last_success = current_time
                print(
                    f"Analyse à {time.strftime('%H:%M:%S')} — {len(prices)} cryptos reçues"
                )
                check_price_changes(prices)

            # Vérifier la déconnexion
            if current_time - last_success > 120 and not disconnect_notified: # 2 minutes
                disconnect_msg = "🔴 BOT DÉCONNECTÉ - Aucune donnée reçue depuis 2 minutes"
                send_telegram_message(disconnect_msg)
                disconnect_notified = True
                print("Notification de déconnexion envoyée")

        except Exception as e:
            error_msg = f"⚠️ Erreur dans le bot : {str(e)}"
            print(error_msg)
            send_telegram_message(error_msg)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run_bot()
