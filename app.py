import requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Weather Dashboard", layout="wide")

st.title("Weather Dashboard")
st.write("This dashboard shows live weather forecast data from Open-Meteo.")

# city coordinates
cities = {
    "Denver": (39.7392, -104.9903),
    "New York": (40.7128, -74.0060),
    "London": (51.5072, -0.1276),
    "Tokyo": (35.6762, 139.6503),
    "Bishkek": (42.8746, 74.5698)
}

# sidebar
st.sidebar.header("Filters")
city = st.sidebar.selectbox("Choose a city", list(cities.keys()))
forecast_days = st.sidebar.slider("Forecast days", 1, 7, 3)
show_temp = st.sidebar.checkbox("Show temperature chart", True)
show_precip = st.sidebar.checkbox("Show precipitation chart", True)

latitude, longitude = cities[city]

# load data
url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": latitude,
    "longitude": longitude,
    "hourly": "temperature_2m,precipitation",
    "current": "temperature_2m",
    "timezone": "auto",
    "forecast_days": forecast_days
}

response = requests.get(url, params=params)
data = response.json()

# create dataframe
df = pd.DataFrame({
    "time": pd.to_datetime(data["hourly"]["time"]),
    "temperature": data["hourly"]["temperature_2m"],
    "precipitation": data["hourly"]["precipitation"]
})

# current weather
st.subheader(f"Current Weather in {city}")
st.metric("Current Temperature (°C)", data["current"]["temperature_2m"])

# line chart
if show_temp:
    st.subheader("Temperature Over Time")
    fig1 = px.line(df, x="time", y="temperature")
    st.plotly_chart(fig1, use_container_width=True)

# bar chart
if show_precip:
    st.subheader("Precipitation Over Time")
    fig2 = px.bar(df, x="time", y="precipitation")
    st.plotly_chart(fig2, use_container_width=True)

# table
st.subheader("Weather Data")
st.dataframe(df)

# download
csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download CSV",
    csv,
    file_name="weather_data.csv",
    mime="text/csv"
)
