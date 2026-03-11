import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
import tweepy
from typing import Optional

# ────────────────────────────────────────
#   VIX & related indices
# ────────────────────────────────────────
vix_indices = ["^VIX1D", "^VIX9D", "^VIN", "^VIX", "^VIF", "^VIX3M", "^VIX6M", "^VIX1Y"]

def get_latest_price(ticker: str) -> Optional[float]:
    """Try to get the most recent price possible from yfinance"""
    t = yf.Ticker(ticker)
    
    try:
        info = t.info
        if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
            return float(info['regularMarketPrice'])
        if 'currentPrice' in info and info['currentPrice'] is not None:
            return float(info['currentPrice'])
    except Exception:
        pass  # info can be empty or fail for some indices

    # Fallback: last available bar (with pre/post market awareness)
    try:
        hist = t.history(period="2d", interval="1d", prepost=True)
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception:
        pass

    print(f"⚠️ Could not retrieve any price for {ticker}")
    return None


# ────────────────────────────────────────
#   Collect VIX term structure
# ────────────────────────────────────────
vix_data = {}
for idx in vix_indices:
    price = get_latest_price(idx)
    if price is not None:
        vix_data[idx] = price
    else:
        print(f"No usable data for {idx}")

# ────────────────────────────────────────
#   QQQ & VVIX
# ────────────────────────────────────────
qqq_price  = get_latest_price("QQQ")
vvix_price = get_latest_price("^VVIX")

qqq_str  = f"{qqq_price:.2f}"  if qqq_price  is not None else "N/A"
vvix_str = f"{vvix_price:.2f}" if vvix_price is not None else "N/A"

print(f"QQQ  → {qqq_str}")
print(f"VVIX → {vvix_str}")

# ────────────────────────────────────────
#   Plot only if we have at least some VIX data
# ────────────────────────────────────────
if vix_data:
    df = pd.DataFrame(list(vix_data.items()), columns=['Index', 'Value'])

    plt.figure(figsize=(11, 6), facecolor="#0e1117")
    plt.gca().set_facecolor("#0e1117")

    plt.plot(df['Index'], df['Value'], marker='o', color='#00d4ff', linewidth=2, markersize=8)
    plt.title("VIX Term Structure (latest available)", color='white', fontsize=16)
    plt.xlabel("Index", color='white')
    plt.ylabel("Value", color='white')
    plt.grid(True, color='gray', alpha=0.4, linestyle='--')

    # Annotate values
    for i, (idx, val) in enumerate(zip(df['Index'], df['Value'])):
        plt.annotate(f"{val:.2f}",
                     (i, val), 
                     xytext=(0, 14),
                     textcoords="offset points",
                     ha='center', va='bottom',
                     color='white', fontsize=10,
                     bbox=dict(boxstyle="round,pad=0.3", fc="#1a1f2e", ec="none", alpha=0.7))

    plt.xticks(color='white', rotation=45, ha='right')
    plt.yticks(color='white')
    plt.tight_layout()

    plt.savefig("vix_term_structure.png", dpi=180, facecolor=plt.gcf().get_facecolor(), bbox_inches='tight')
    plt.close()   # comment out if you want to see the plot interactively
    # plt.show()
else:
    print("No VIX data retrieved → skipping plot.")
    # You may want to exit here or post a warning tweet instead
    # import sys; sys.exit(1)


# ────────────────────────────────────────
#   Twitter part (OAuth 1 + Client v2)
# ────────────────────────────────────────
consumer_key        = ""    # ← fill
consumer_secret     = ""
access_token        = ""
access_token_secret = ""

# OAuth 1.0a (needed for media upload)
auth = tweepy.OAuth1UserHandler(
    consumer_key, consumer_secret,
    access_token, access_token_secret
)
api = tweepy.API(auth)

# v2 Client (for create_tweet)
client = tweepy.Client(
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    access_token=access_token,
    access_token_secret=access_token_secret
)

try:
    media = api.media_upload("vix_term_structure.png")
    tweet_text = f"$QQQ {qqq_str}\n$VVIX {vvix_str}\nVIX9D strong"

    response = client.create_tweet(
        text=tweet_text,
        media_ids=[media.media_id]
    )
    tweet_url = f"https://x.com/user/status/{response.data['id']}"
    print("Tweet posted:", tweet_url)
except Exception as e:
    print("Twitter posting failed:", str(e))
