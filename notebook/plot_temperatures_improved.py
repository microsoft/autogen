# filename: plot_temperatures_improved.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns  # For colorblind-friendly palette

# Ensure you have seaborn installed: pip install seaborn

# URL of the CSV file
url = "https://raw.githubusercontent.com/vega/vega/main/docs/data/seattle-weather.csv"

# Read the data from the URL
data = pd.read_csv(url)

# Extract the Date, Temperature High, and Temperature Low columns
dates = pd.to_datetime(data["date"])
temp_high = data["temp_max"].rolling(window=7).mean()  # 7-day rolling average
temp_low = data["temp_min"].rolling(window=7).mean()  # 7-day rolling average

# Plot the high and low temperatures using seaborn's colorblind-friendly palette
plt.figure(figsize=(10, 5), dpi=150)
plt.plot(dates, temp_high, label="High Temperature", color=sns.color_palette("colorblind")[2], linewidth=1)
plt.plot(dates, temp_low, label="Low Temperature", color=sns.color_palette("colorblind")[0], linewidth=1)
plt.xlabel("Date", fontsize=12)
plt.ylabel("Temperature (°C)", fontsize=12)
plt.title("High and Low Temperatures in Seattle (7-day Rolling Average)", fontsize=14)

# Adjusting the legend
leg = plt.legend(loc="upper left", frameon=True)
leg.get_frame().set_alpha(0.5)

# Adjusting the grid
plt.grid(True, linestyle="--", linewidth=0.5, color="grey", alpha=0.7)

# Increase tick label size
plt.tick_params(labelsize=10)

# Save the figure with high resolution
plt.savefig("result.jpg", format="jpg", dpi=150)

# Show the plot
plt.show()
