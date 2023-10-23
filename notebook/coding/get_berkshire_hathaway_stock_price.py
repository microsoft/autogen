import requests
from bs4 import BeautifulSoup
from datetime import datetime
import matplotlib.pyplot as plt

# Create a dictionary to store cached stock prices
cache = {}

def get_stock_price(symbol):
    """Get the stock price of a given symbol."""
    if symbol in cache:
        return cache[symbol]
    url = f"https://finance.yahoo.com/quote/{symbol}"
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser")
    price_elem = soup.find("span", attrs={"class": "Trsdu(0.3s) Fw(b) Fz(36px) Mb(-4px) D(ib)"})
    if price_elem is not None:
        price = float(price_elem.text)
        cache[symbol] = price
        return price
    else:
        return None

def get_percentage_gain(start_price, end_price):
    """Calculate the percentage gain between two stock prices."""
    if start_price is None or end_price is None:
        return None
    return (end_price - start_price) / start_price * 100

def main():
    """Get the percentage gain YTD for Berkshire Hathaway stock and plot a chart."""
    try:
        import matplotlib.dates as mdates

        start_date = "2022-01-01"
        end_date = "2023-01-01"
        start_price = get_stock_price("BRK-A")
        end_price = get_stock_price("BRK-B")
        percentage_gain = get_percentage_gain(start_price, end_price)
        if percentage_gain is not None:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            prices = [start_price, end_price]
            prices = [p for p in prices if p is not None]
            dates = [start_date_obj, end_date_obj]
            dates = dates[:len(prices)]
            dates = mdates.date2num(dates)
            plt.plot(dates, prices)
            plt.title("Berkshire Hathaway Stock Price")
            plt.xlabel("Date")
            plt.ylabel("Price")
            plt.savefig("linechart.png")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()