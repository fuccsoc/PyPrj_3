import requests
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
import logging

load_dotenv()

API_KEY = os.getenv("ACCUWEATHER_API_KEY")
BASE_URL = "http://dataservice.accuweather.com"

logging.basicConfig(level=logging.INFO)

app = dash.Dash(__name__)
server = app.server

def fetch_weather_data_by_coords(lat, lon, days):
    location_url = f"{BASE_URL}/locations/v1/cities/geoposition/search"
    forecast_url = f"{BASE_URL}/forecasts/v1/daily/{days}day/"
    location_params = {"apikey": API_KEY, "q": f"{lat},{lon}"}
    
    logging.info(f"Requesting location data with params: {location_params}")
    location_response = requests.get(location_url, params=location_params)
    logging.info(f"Location response: {location_response.status_code} - {location_response.text}")
    
    if location_response.status_code != 200:
        return None
    location_data = location_response.json()
    location_key = location_data.get("Key")
    forecast_params = {"apikey": API_KEY, "metric": True}
    
    logging.info(f"Requesting forecast data with params: {forecast_params}")
    forecast_response = requests.get(
        f"{forecast_url}{location_key}", params=forecast_params
    )
    logging.info(f"Forecast response: {forecast_response.status_code} - {forecast_response.text}")
    
    if forecast_response.status_code != 200:
        return None
    return forecast_response.json()

def fetch_weather_data_by_city(city_name, days):
    location_url = f"{BASE_URL}/locations/v1/cities/search"
    forecast_url = f"{BASE_URL}/forecasts/v1/daily/{days}day/"
    location_params = {"apikey": API_KEY, "q": city_name}
    
    logging.info(f"Requesting location data with params: {location_params}")
    location_response = requests.get(location_url, params=location_params)
    logging.info(f"Location response: {location_response.status_code} - {location_response.text}")
    
    if location_response.status_code != 200:
        return None
    location_data = location_response.json()
    if not location_data:
        return None
    location_key = location_data[0].get("Key")
    forecast_params = {"apikey": API_KEY, "metric": True}
    
    logging.info(f"Requesting forecast data with params: {forecast_params}")
    forecast_response = requests.get(
        f"{forecast_url}{location_key}", params=forecast_params
    )
    logging.info(f"Forecast response: {forecast_response.status_code} - {forecast_response.text}")
    
    if forecast_response.status_code != 200:
        return None
    return forecast_response.json()

app.layout = html.Div(
    [
        html.H1("Прогноз погоды для вашего маршрута"),
        html.Div(
            [
                html.Label("Добавить точки маршрута (название города или широта, долгота):"),
                html.Button("Добавить точку", id="add-point", n_clicks=0),
                html.Div(id="waypoints-container", children=[]),
            ],
            style={"margin-bottom": "20px"},
        ),
        html.Div(
            [
                html.Label("Выберите количество дней прогноза:"),
                dcc.Dropdown(
                    id="forecast-days",
                    options=[
                        {"label": "1 день", "value": 1},
                        {"label": "3 дня", "value": 3},
                        {"label": "5 дней", "value": 5},
                    ],
                    value=5,
                    clearable=False,
                ),
            ],
            style={"margin-bottom": "20px"},
        ),
        html.Button("Получить прогноз", id="get-weather", n_clicks=0),
        dcc.Graph(id="weather-graph"),
        html.Div(id="error-message", style={"color": "red"}),
    ]
)

@app.callback(
    Output("waypoints-container", "children"),
    Input("add-point", "n_clicks"),
    State("waypoints-container", "children"),
)
def add_waypoint_fields(n_clicks, children):
    new_point = html.Div(
        [
            dcc.Input(
                type="text",
                placeholder="Название города (необязательно)",
                id={"type": "city", "index": n_clicks},
            ),
            dcc.Input(
                type="number",
                placeholder="Широта",
                id={"type": "lat", "index": n_clicks},
            ),
            dcc.Input(
                type="number",
                placeholder="Долгота",
                id={"type": "lon", "index": n_clicks},
            ),
        ],
        style={"margin-bottom": "10px"},
    )
    children.append(new_point)
    return children

@app.callback(
    [
        Output("weather-graph", "figure"),
        Output("error-message", "children"),
    ],
    Input("get-weather", "n_clicks"),
    [
        State({"type": "city", "index": dash.dependencies.ALL}, "value"),
        State({"type": "lat", "index": dash.dependencies.ALL}, "value"),
        State({"type": "lon", "index": dash.dependencies.ALL}, "value"),
        State("forecast-days", "value"),
    ],
)
def update_weather(n_clicks, cities, latitudes, longitudes, days):
    if n_clicks == 0:
        return go.Figure(), ""

    weather_data = []
    for city, lat, lon in zip(cities, latitudes, longitudes):
        if city:
            data = fetch_weather_data_by_city(city, days)
        elif lat is not None and lon is not None:
            data = fetch_weather_data_by_coords(lat, lon, days)
        else:
            data = None

        if data:
            weather_data.append((city or f"{lat}, {lon}", data))

    temp_fig = go.Figure()

    for idx, (location, data) in enumerate(weather_data):
        forecasts = data["DailyForecasts"]
        dates = [day["Date"][:10] for day in forecasts]
        temps = [day["Temperature"]["Maximum"]["Value"] for day in forecasts]

        temp_fig.add_trace(
            go.Scatter(
                x=dates,
                y=temps,
                mode="lines+markers",
                name=f"Точка {idx + 1} ({location}) Температура (°C)",
            )
        )

    temp_fig.update_layout(
        title=f"{days}-дневный прогноз погоды",
        xaxis_title="Дата",
        yaxis_title="Температура (°C)",
        legend_title="Местоположение",
    )

    return temp_fig, ""

if __name__ == "__main__":
    app.run_server(debug=True)
