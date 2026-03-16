import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from typing import Optional, Dict
import datetime
import pyodbc  # For SQL Server connection

# ────────────────────────────────────────
#   Database Configuration
# ────────────────────────────────────────
# Update these with your local SQL Server details
SERVER = 'localhost'          # Or your server name, e.g., 'localhost\SQLEXPRESS'
DATABASE = 'FinanceDB'        # Create this database in SQL Server Management Studio if it doesn't exist
TABLE_NAME = 'VIXHistory'
DRIVER = '{ODBC Driver 17 for SQL Server}'  # Check your installed ODBC drivers; common ones: 'SQL Server' or 'ODBC Driver 18 for SQL Server'

# Connection string (using Windows Authentication for local setup)
CONN_STR = f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'

# ────────────────────────────────────────
#   VIX & related indices
# ────────────────────────────────────────
VIX_INDICES = ["^VIX1D", "^VIX9D", "^VIN", "^VIX", "^VIF", "^VIX3M", "^VIX6M", "^VIX1Y"]
PLOT_FILE = "vix_term_structure.png"

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

def fetch_vix_data() -> Dict[str, Optional[float]]:
    """Fetch latest VIX term structure data"""
    vix_data = {}
    for idx in VIX_INDICES:
        price = get_latest_price(idx)
        vix_data[idx] = price
        if price is None:
            print(f"No usable data for {idx}")
    return vix_data

def fetch_qqq_and_vvix() -> tuple[Optional[float], Optional[float]]:
    """Fetch latest QQQ and VVIX prices"""
    qqq_price = get_latest_price("QQQ")
    vvix_price = get_latest_price("^VVIX")
    return qqq_price, vvix_price

def store_in_db(vix_data: Dict[str, Optional[float]], qqq_price: Optional[float], vvix_price: Optional[float]) -> None:
    """Store fetched data in SQL Server"""
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()

        # Create table if it doesn't exist
        create_table_query = f"""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{TABLE_NAME}' AND xtype='U')
        CREATE TABLE {TABLE_NAME} (
            PullTimestamp DATETIME NOT NULL,
            VIX1D FLOAT NULL,
            VIX9D FLOAT NULL,
            VIN FLOAT NULL,
            VIX FLOAT NULL,
            VIF FLOAT NULL,
            VIX3M FLOAT NULL,
            VIX6M FLOAT NULL,
            VIX1Y FLOAT NULL,
            QQQ FLOAT NULL,
            VVIX FLOAT NULL
        )
        """
        cursor.execute(create_table_query)
        conn.commit()

        # Insert the current data
        now = datetime.datetime.now()
        insert_query = f"""
        INSERT INTO {TABLE_NAME} (PullTimestamp, VIX1D, VIX9D, VIN, VIX, VIF, VIX3M, VIX6M, VIX1Y, QQQ, VVIX)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            now,
            vix_data.get("^VIX1D"),
            vix_data.get("^VIX9D"),
            vix_data.get("^VIN"),
            vix_data.get("^VIX"),
            vix_data.get("^VIF"),
            vix_data.get("^VIX3M"),
            vix_data.get("^VIX6M"),
            vix_data.get("^VIX1Y"),
            qqq_price,
            vvix_price
        )
        cursor.execute(insert_query, values)
        conn.commit()

        print(f"Data inserted successfully at {now}")
    except pyodbc.Error as e:
        print(f"SQL Server error: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def generate_plot(vix_data: Dict[str, Optional[float]]) -> bool:
    """Generate and save VIX term structure plot; return True if plot was created"""
    # Filter out None values for plotting
    plot_data = {k: v for k, v in vix_data.items() if v is not None}
    if not plot_data:
        print("No VIX data retrieved → skipping plot.")
        return False

    df = pd.DataFrame(list(plot_data.items()), columns=['Index', 'Value'])

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

    plt.savefig(PLOT_FILE, dpi=180, facecolor=plt.gcf().get_facecolor(), bbox_inches='tight')
    # plt.close()   # comment out if you want to see the plot interactively
    plt.show()

    print(f"Plot saved to {PLOT_FILE}")
    return True

# ────────────────────────────────────────
#   Main execution
# ────────────────────────────────────────
if __name__ == "__main__":
    vix_data = fetch_vix_data()
    qqq_price, vvix_price = fetch_qqq_and_vvix()

    qqq_str = f"{qqq_price:.2f}" if qqq_price is not None else "N/A"
    vvix_str = f"{vvix_price:.2f}" if vvix_price is not None else "N/A"
    print(f"QQQ  → {qqq_str}")
    print(f"VVIX → {vvix_str}")

    store_in_db(vix_data, qqq_price, vvix_price)
    generate_plot(vix_data)
