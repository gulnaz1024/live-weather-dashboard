import requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Live Weather Dashboard",
    page_icon="🌦️",
    layout="wide"
)

st.title("🌦️ Live Weather Dashboard")
st.markdown(
    "This dashboard uses live weather forecast data from Open-Meteo. "
    "Search for a city, choose the forecast length, and explore temperature, precipitation, and wind trends."
)

# -----------------------------
# API helper functions
# -----------------------------
@st.cache_data(ttl=3600)
def geocode_city(city_name: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city_name,
        "count": 10,
        "language": "en",
        "format": "json"
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data.get("results", [])


@st.cache_data(ttl=1800)
def load_weather(latitude: float, longitude: float, forecast_days: int):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,precipitation,wind_speed_10m,relative_humidity_2m,weather_code",
        "current": "temperature_2m,wind_speed_10m,relative_humidity_2m,weather_code",
        "timezone": "auto",
        "forecast_days": forecast_days
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def build_hourly_dataframe(data: dict) -> pd.DataFrame:
    hourly = data["hourly"]
    df = pd.DataFrame({
        "time": pd.to_datetime(hourly["time"]),
        "temperature_2m": hourly["temperature_2m"],
        "precipitation": hourly["precipitation"],
        "wind_speed_10m": hourly["wind_speed_10m"],
        "relative_humidity_2m": hourly["relative_humidity_2m"],
        "weather_code": hourly["weather_code"],
    })

    numeric_cols = [
        "temperature_2m",
        "precipitation",
        "wind_speed_10m",
        "relative_humidity_2m",
        "weather_code",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Controls")

city_query = st.sidebar.text_input("Enter a city", value="Denver")

results = []
selected_location = None

if city_query.strip():
    try:
        results = geocode_city(city_query.strip())
    except Exception as e:
        st.error(f"Error loading city data: {e}")

if results:
    location_options = [
        f"{r['name']}, {r.get('admin1', '')}, {r.get('country', '')}".replace(", ,", ",").strip(", ")
        for r in results
    ]
    selected_label = st.sidebar.selectbox("Choose a location", location_options, index=0)
    selected_index = location_options.index(selected_label)
    selected_location = results[selected_index]
else:
    st.warning("No city results found. Try another city name.")
    st.stop()

forecast_days = st.sidebar.selectbox("Forecast range (days)", [1, 3, 5, 7], index=2)
max_precip = st.sidebar.slider("Maximum precipitation to display (mm)", 0, 50, 20)
show_only_daytime = st.sidebar.checkbox("Show only daytime hours", value=False)

latitude = selected_location["latitude"]
longitude = selected_location["longitude"]
city_name = selected_location["name"]
country = selected_location.get("country", "")
admin1 = selected_location.get("admin1", "")

# -----------------------------
# Load weather data
# -----------------------------
try:
    weather_data = load_weather(latitude, longitude, forecast_days)
    df = build_hourly_dataframe(weather_data)
except Exception as e:
    st.error(f"Error loading weather data: {e}")
    st.stop()

if show_only_daytime:
    df = df[(df["time"].dt.hour >= 6) & (df["time"].dt.hour <= 18)]

df = df[df["precipitation"] <= max_precip].copy()

current = weather_data.get("current", {})

# -----------------------------
# Summary
# -----------------------------
st.subheader(f"Weather forecast for {city_name}, {admin1}, {country}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Current Temp (°C)", current.get("temperature_2m", "N/A"))
c2.metric("Current Wind (km/h)", current.get("wind_speed_10m", "N/A"))
c3.metric("Current Humidity (%)", current.get("relative_humidity_2m", "N/A"))
c4.metric("Forecast Hours", len(df))

st.divider()

# -----------------------------
# Charts
# -----------------------------
left, right = st.columns(2)

with left:
    fig_temp = px.line(
        df,
        x="time",
        y="temperature_2m",
        title="Temperature Over Time",
        markers=True
    )
    st.plotly_chart(fig_temp, use_container_width=True)

with right:
    fig_precip = px.bar(
        df,
        x="time",
        y="precipitation",
        title="Precipitation Over Time"
    )
    st.plotly_chart(fig_precip, use_container_width=True)

fig_wind = px.scatter(
    df,
    x="time",
    y="wind_speed_10m",
    size="relative_humidity_2m",
    hover_data=["temperature_2m", "precipitation", "weather_code"],
    title="Wind Speed Over Time (bubble size = humidity)"
)
st.plotly_chart(fig_wind, use_container_width=True)

map_df = pd.DataFrame({
    "latitude": [latitude],
    "longitude": [longitude],
    "city": [city_name]
})
st.subheader("Location Map")
st.map(map_df, use_container_width=True)

# -----------------------------
# Data table + download
# -----------------------------
st.subheader("Hourly Forecast Data")
st.dataframe(df, use_container_width=True)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download forecast as CSV",
    data=csv,
    file_name=f"{city_name.lower().replace(' ', '_')}_forecast.csv",
    mime="text/csv"
)