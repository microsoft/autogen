# filename: plot_temperatures.py
import pandas as pd
import matplotlib.pyplot as plt

# URL of the CSV file
url = "https://raw.githubusercontent.com/vega/vega/main/docs/data/seattle-weather.csv"

# Read the data from the URL
data = pd.read_csv(url)

# Extract the Date, Temperature High, and Temperature Low columns
dates = pd.to_datetime(data["date"])
temp_high = data["temp_max"]
temp_low = data["temp_min"]

# Plot the high and low temperatures
plt.figure(figsize=(10, 5))
plt.plot(dates, temp_high, label="High Temperature", color="r")
plt.plot(dates, temp_low, label="Low Temperature", color="b")
plt.xlabel("Date")
plt.ylabel("Temperature (°C)")
plt.title("High and Low Temperatures in Seattle")
plt.legend()
plt.grid(True)

# Save the figure
plt.savefig("result.jpg")

# Show the plot
plt.show()
