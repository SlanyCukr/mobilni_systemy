import json
import dash
from dash import dcc, html, Dash
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from datetime import datetime
import json
import paho.mqtt.client as mqtt

DATA = []
SAMPLE_DATA = {'time': '2023-10-04 11:26:39', 'inHumidity': '36.0', 'inTemp_C': '25.0', 'outHumidity': '41.0', 'outTemp_C': '20.200000000000003', 'pressure_mbar': '994.1', 'windSpeed_mps': '1.4000000011200002', 'windGust_mps': '1.70000000136', 'windDir': '45.0', 'rain_mm': '0.0', 'status': '0.0', 'ptr': '39744.0', 'delay': '1.0', 'rxCheckPercent': '100.0', 'outTempBatteryStatus': '0.0', 'rainTotal': '131.13', 'usUnits': '17.0', 'altimeter_mbar': '1030.1961248201087', 'appTemp_C': '18.41478228035239', 'barometer_mbar': '1029.45552136088', 'cloudbase_meter': '1967.839983995644', 'dewpoint_C': '6.52017610402867', 'heatindex_C': '19.346111111111124', 'humidex_C': '20.200000000000003', 'inDewpoint_C': '8.878814216502521', 'rainRate_mm_per_hour': '0.0', 'windchill_C': '20.200000000000006', 'hourRain_mm': '0.0', 'rain24_mm': '0.9000000000000341', 'dayRain_mm': '0.9000000000000341'}


def on_connect(client: mqtt.Client, userdata, flags, rc):
    """

    :param client:
    :param userdata:
    :param flags:
    :param rc:
    :return:
    """
    print(f"Connected with result code {rc}")

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("/devices/wh1080-fei-json")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    payload_dict = json.loads(msg.payload)

    payload_dict["time"] = datetime.utcfromtimestamp(int(payload_dict['time'])).strftime('%Y-%m-%d %H:%M:%S')

    # if message with same time is already added, ignore this message
    if len(DATA) > 0 and DATA[-1]['time'] == payload_dict['time']:
        return

    print(f"Got new data: {payload_dict}")

    DATA.append(payload_dict)


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
                x=[entry['time'] for entry in DATA],
                y=[float(entry[selected_value]) for entry in DATA],
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
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("pcfeib425t.vsb.cz", 1883, 60)

    #client.loop_forever()
    client.loop_start()

    app.run_server(debug=True)