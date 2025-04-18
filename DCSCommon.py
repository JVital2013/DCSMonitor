import json
import logging
import configparser
from datetime import datetime, timedelta
from pathlib import Path
from influxdb import InfluxDBClient

# Read configuration
config = configparser.ConfigParser()
config_path = Path(__file__).parent / 'config.ini'
if not config_path.exists():
    raise FileNotFoundError(f"Configuration file not found: {config_path}")

config.read(config_path)

# Set up logging
logging.basicConfig(
    level=logging.INFO,  # Always set to INFO level
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get conditional logging settings
LOG_BLOCKS = config.getboolean('logging', 'log_blocks', fallback=False)
LOG_SKIPPED = config.getboolean('logging', 'log_skipped', fallback=False)

def create_influx_client():
    try:
        # Create v2 client
        client = InfluxDBClient(
            host=config['influxdb']['host'],
            port=int(config['influxdb']['port']),
            username=config['influxdb']['token'],
            password=config['influxdb']['token'],
            database=config['influxdb']['bucket']
        )
        # Test v2 connection
        client.ping()
        return client
    except Exception as e:
        logger.error(f"Failed to connect to InfluxDB: {str(e)}")
    

def write_points(client, json_body):
    """Write points to InfluxDB"""
    client.write_points(json_body)

def process_dcs_data(client, data):
    """Process DCS data and write to InfluxDB"""
    # Skip if no blocks
    if not data.get('blocks'):
        logger.info("Skipping: No data blocks")
        return
        
    for block in data['blocks']:
        # Skip if no dcp info
        if 'dcp' not in block:
            logger.info("Skipping block: No DCP info")
            continue
            
        # Extract station info
        station = block['dcp']['description']
        lat = block['dcp']['lat']
        lon = block['dcp']['lon']
        
        if LOG_BLOCKS:
            logger.info(f"Processing block for station: {station}")
        
        # Get address based on message type
        if block.get('type') == 'Missed Message':
            address = block['header'].get('platform_address', 'unknown')
        else:
            address = block['header'].get('corrected_address', 'unknown')
        
        # Handle different message types
        if block.get('type') == 'Missed Message':
            # For missed messages, we can still record the station info
            # but with a special measurement to indicate missed data
            json_body = [{
                "measurement": "missed_message",
                "tags": {
                    "station": station,
                    "lat": lat,
                    "lon": lon,
                    "address": address
                },
                "fields": {
                    "value": 1
                },
                "time": block['header']['window_start']
            }]
            try:
                write_points(client, json_body)
            except Exception as e:
                logger.error(f"Failed to write missed message for {station}: {str(e)}")
                
        elif 'data_values' in block:
            # Process regular data values
            for value_set in block['data_values']:
                measurement = value_set['name']
                carrier_start = datetime.strptime(block['header']['carrier_start'], '%Y-%m-%d %H:%M:%S.%f')
                
                # Find the matching PE info for this measurement
                read_to_transmit_offset = 0
                record_interval = 0
                for pe_info in block['dcp'].get('pe_info', []):
                    if pe_info['name'] == measurement:
                        read_to_transmit_offset = pe_info.get('read_to_transmit_offset', 0)
                        record_interval = pe_info.get('record_interval', 0)
                        break
                
                # Calculate the timestamp for each value
                for i, value in enumerate(value_set['values']):
                    try:
                        # Skip if value cannot be converted to float
                        float_value = float(value)
                    except (ValueError, TypeError):
                        if LOG_SKIPPED:
                            logger.info(f"Skipping unparseable value for {station} - {measurement}: {value}")
                        continue
                        
                    # First value is offset by read_to_transmit_offset minutes before carrier_start
                    # Each subsequent value is record_interval minutes before the previous one
                    minutes_offset = read_to_transmit_offset + (i * record_interval)
                    timestamp = carrier_start - timedelta(minutes=minutes_offset)
                    
                    json_body = [{
                        "measurement": measurement,
                        "tags": {
                            "station": station,
                            "lat": lat,
                            "lon": lon,
                            "address": address
                        },
                        "fields": {
                            "value": float_value
                        },
                        "time": timestamp
                    }]
                    
                    try:
                        write_points(client, json_body)
                    except Exception as e:
                        logger.error(f"Failed to write data for {station} - {measurement}: {str(e)}")
        else:
            logger.info("Skipping block: No data values") 