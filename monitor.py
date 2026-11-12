import json, os, re, sys
import requests
from bs4 import BeautifulSoup

URL = "https://www.todis.it/prenotabili/"
STATE = "state.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; todis-monitor/1.0)"}


def scrape():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    found = {}
    for a in soup.find_all("a", href=re.compile(r"/prenotabile/[^/]+/?$")):
        href = a["href"]
        card = a.find_parent(lambda t: t.find("h3") is not None) or a
        h3 = card.find("h3")
        text = card.get_text(" ", strip=True)
        price = re.search(r"€\s*[\d.,]+", text)
        found[href] = {
            "title": h3.get_text(strip=True) if h3 else href.rstrip("/").split("/")[-1],
            "price": price.group(0) if price else "",
        }
    return found


def notify(msg):
    print(msg)
    webhook = os.getenv("DISCORD_WEBHOOK")
    if webhook:
        requests.post(webhook, json={"content": msg}, timeout=30)


def main():
    current = scrape()
    if not current:
        # Pagina cambiata o errore: non sovrascrivere lo stato, evita falsi allarmi
        notify("⚠️ Todis monitor: nessun prodotto trovato, controlla lo script.")
        sys.exit(1)

    first_run = not os.path.exists(STATE)
    old = {} if first_run else json.load(open(STATE))
    new = {u: p for u, p in current.items() if u not in old}

    if new and not first_run:
        for url, p in new.items():
            notify(f"🆕 Nuovo prenotabile Todis!\n{p['title']} {p['price']}\n{url}")

    if first_run or new:
        json.dump(current, open(STATE, "w"), ensure_ascii=False, indent=2)
        print(f"Stato salvato: {len(current)} prodotti")
    else:
        print("Nessuna novità")


if __name__ == "__main__":
    main()
