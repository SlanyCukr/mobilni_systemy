from collections import defaultdict
from typing import List

import dash
from dash import dcc, html, Dash
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from datetime import datetime
import json

from mqtt_app import MqttApp

DATA = defaultdict(list)
SAMPLE_DATA = {'time': '2023-10-04 11:26:39', 'inHumidity': '36.0', 'inTemp_C': '25.0', 'outHumidity': '41.0', 'outTemp_C': '20.200000000000003', 'pressure_mbar': '994.1', 'windSpeed_mps': '1.4000000011200002', 'windGust_mps': '1.70000000136', 'windDir': '45.0', 'rain_mm': '0.0', 'status': '0.0', 'ptr': '39744.0', 'delay': '1.0', 'rxCheckPercent': '100.0', 'outTempBatteryStatus': '0.0', 'rainTotal': '131.13', 'usUnits': '17.0', 'altimeter_mbar': '1030.1961248201087', 'appTemp_C': '18.41478228035239', 'barometer_mbar': '1029.45552136088', 'cloudbase_meter': '1967.839983995644', 'dewpoint_C': '6.52017610402867', 'heatindex_C': '19.346111111111124', 'humidex_C': '20.200000000000003', 'inDewpoint_C': '8.878814216502521', 'rainRate_mm_per_hour': '0.0', 'windchill_C': '20.200000000000006', 'hourRain_mm': '0.0', 'rain24_mm': '0.9000000000000341', 'dayRain_mm': '0.9000000000000341'}


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    value = msg.payload.decode("utf-8")
    topic = msg.topic
    value_name = topic.split("/")[-1]

    DATA[value_name].append((value, datetime.now()))

    print(f"Received {value_name}: {value} at {datetime.now()}")

    save_data()


def get_previous_data() -> List[dict]:
    """
    Load previous data from file.
    :return: Previous data.
    """
    # if file does not exist, return empty list
    try:
        with open('previous_data.json', 'r') as f:
            data = json.load(f)

            return data
    except FileNotFoundError:
        return defaultdict(list)
    except Exception as e:
        return defaultdict(list)


def save_data():
    """
    Save data to file.
    """
    with open('previous_data.json', 'w') as f:
        f.write(json.dumps(DATA, indent=4, sort_keys=True, default=str))


app = dash.Dash(__name__)

# Extract keys from the first item in data (excluding the 'time' key)
keys = [key for key in SAMPLE_DATA.keys() if key != 'time']

# Generate dropdown options using a list comprehension
options = [{'label': key.replace('_', ' ').title(), 'value': key} for key in keys]


app.layout = html.Div([
    dcc.Dropdown(
        id='dropdown-selector',
        options=options,
        value=keys[0],  # Setting the first key as the default value
        clearable=False
    ),
    dcc.Graph(id='value-graph'),
    dcc.Interval(
        id='interval-component',
        interval=5*1000,  # in milliseconds
        n_intervals=0
    )
])


@app.callback(
    Output('value-graph', 'figure'),
    Input('dropdown-selector', 'value'),
    Input('interval-component', 'n_intervals')  # Added input to trigger the update every 5 seconds
)
def update_graph(selected_value, n):  # 'n' is not used in the function but is required for the callback trigger
    return {
        'data': [
            go.Scatter(
                x=[x[1] for x in DATA[selected_value]],
                y=[x[0] for x in DATA[selected_value]],
                mode='lines+markers',
                name=selected_value
            )
        ],
        'layout': go.Layout(
            title=f'{selected_value} over Time',
            xaxis=dict(title='Time'),
            yaxis=dict(title=selected_value),
        )
    }


if __name__ == '__main__':
    DATA = get_previous_data()

    mqtt_app = MqttApp(
        host="localhost",
        port=8883,
        on_message=on_message,
        topic="/devices/wh1080-fei/#",
        user="tempUser",
        password="tempUser1234"
    )

    app.run_server(debug=True)
