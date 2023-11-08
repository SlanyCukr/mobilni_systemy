import gpxpy
import gpxpy.gpx
from datetime import datetime
import argparse
from math import radians, cos, sin, asin, sqrt


# Define NMEA Sentence Parsing
def parse_gpgga(sentence):
    fields = sentence.split(',')

    # Get time
    time_str = fields[1]
    hours = int(time_str[0:2])
    minutes = int(time_str[2:4])
    seconds = float(time_str[4:])

    # Get latitude
    lat_str = fields[2]
    lat_direction = fields[3]
    lat_deg = float(lat_str[0:2])
    lat_min = float(lat_str[2:])
    latitude = lat_deg + lat_min / 60.0
    if lat_direction == 'S':
        latitude *= -1

    # Get longitude
    lon_str = fields[4]
    lon_direction = fields[5]
    lon_deg = float(lon_str[0:3])
    lon_min = float(lon_str[3:])
    longitude = lon_deg + lon_min / 60.0
    if lon_direction == 'W':
        longitude *= -1

    # Get altitude
    altitude = float(fields[9])

    return (hours, minutes, seconds, latitude, longitude, altitude)


def parse_gprmc(sentence):
    fields = sentence.split(',')

    # Get date
    date_str = fields[9]
    day = int(date_str[0:2])
    month = int(date_str[2:4])
    year = int(date_str[4:6]) + 2000  # Assuming a YY format which is common in NMEA sentences

    # Get status (A=active, V=void)
    status = fields[2]

    return (day, month, year, status)

# distance_threshold=0.00005


def should_create_new_path(prev_point, current_point, max_time_diff, max_lat_lon_diff, distance_in_meters=None):
    time_diff = (current_point[0] - prev_point[0]).total_seconds()
    if time_diff > max_time_diff:
        return True

    if distance_in_meters is not None:
        distance = haversine(prev_point[2], prev_point[1], current_point[2], current_point[1])
        if distance > distance_in_meters:
            return True
    else:
        lat_diff = abs(current_point[1] - prev_point[1])
        lon_diff = abs(current_point[2] - prev_point[2])
        if lat_diff > max_lat_lon_diff or lon_diff > max_lat_lon_diff:
            return True

    return False


def create_gpx_track(gps_data, max_time_diff, max_lat_lon_diff, distance_in_meters=None):
    gpx = gpxpy.gpx.GPX()

    # Create first track in our GPX:
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)

    # Create the first segment in our GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    prev_point = None

    for data_point in gps_data:
        time, latitude, longitude, altitude = data_point

        # If we have a previous point, check if we should start a new segment
        if prev_point and should_create_new_path(prev_point, (time, latitude, longitude, altitude), max_time_diff, max_lat_lon_diff, distance_in_meters):
            # Start a new segment
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            gpx_track.segments.append(gpx_segment)

        # Add point to current segment
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude, longitude, elevation=altitude, time=time))

        # Update the previous point
        prev_point = (time, latitude, longitude, altitude)

    return gpx


# Parse the NMEA sentences and create a GPX file
def nmea_to_gps_data(nmea_sentences):
    gps_data = []
    current_date = None

    for sentence in nmea_sentences:
        if sentence.startswith('$GPGGA'):
            time_data = parse_gpgga(sentence)
            if current_date is not None:
                time = datetime(current_date[2], current_date[1], current_date[0],
                                         time_data[0], time_data[1], int(time_data[2]),
                                         int((time_data[2] % 1) * 1e6))
                gps_data.append((time,) + time_data[3:])
        elif sentence.startswith('$GPRMC'):
            date_data = parse_gprmc(sentence)
            if date_data[3] == 'A':  # We'll take only active RMC sentences for the date
                current_date = date_data[:3]
    return gps_data


def load_nmea_sentences(nmea_file_path):
    with open(nmea_file_path) as f:
        nmea_sentences = f.readlines()
    return nmea_sentences


def calculate_averages(gps_data):
    if len(gps_data) < 2:
        return None

    total_time_diff = sum((gps_data[i][0] - gps_data[i-1][0]).total_seconds() for i in range(1, len(gps_data)))
    average_time_diff = total_time_diff / (len(gps_data) - 1)

    total_lat_diff = sum(abs(gps_data[i][1] - gps_data[i-1][1]) for i in range(1, len(gps_data)))
    average_lat_diff = total_lat_diff / (len(gps_data) - 1)

    total_lon_diff = sum(abs(gps_data[i][2] - gps_data[i-1][2]) for i in range(1, len(gps_data)))
    average_lon_diff = total_lon_diff / (len(gps_data) - 1)

    return average_time_diff, average_lat_diff, average_lon_diff


def haversine(lon1, lat1, lon2, lat2):
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of Earth in kilometers
    return c * r


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert NMEA sentences to GPX format.')
    parser.add_argument('--max_time_diff', type=int, default=5,
                        help='Maximum time difference between points in seconds')
    parser.add_argument('--max_lat_lon_diff', type=float, default=0.0001,
                        help='Maximum latitude/longitude difference between points')
    parser.add_argument('--distance_in_meters', type=float, default=None,
                        help='Maximum distance between points in meters')
    args = parser.parse_args()

    print("Converting NMEA to GPX...")

    nmea_sentences = load_nmea_sentences("2015-08-12.nmea")

    # remove \n from each sentence
    nmea_sentences = [sentence.strip() for sentence in nmea_sentences]

    # Parse the NMEA sentences
    gps_data = nmea_to_gps_data(nmea_sentences)

    # Use the average values calculated or set your own thresholds
    max_time_diff = 5
    max_lat_lon_diff = 0.0001
    distance_in_meters = None

    # Convert NMEA to GPX using the new thresholds
    gpx = create_gpx_track(gps_data, max_time_diff, max_lat_lon_diff, distance_in_meters)

    # Save to a file
    with open('output.gpx', 'w') as f:
        f.write(gpx.to_xml())

    print("GPX data written to 'output.gpx'")
