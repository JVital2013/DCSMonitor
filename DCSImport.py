import glob
import os
import json
from DCSCommon import create_influx_client, process_dcs_data, logger, config

def import_historical_data(client, data_dir):
    """Import historical DCS data from JSON files in the specified directory"""
    if not os.path.exists(data_dir):
        logger.error(f"Data directory does not exist: {data_dir}")
        return
        
    for filename in glob.glob(os.path.join(data_dir, "*.dcs.json")):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            process_dcs_data(client, data)
            logger.info(f"Processed {filename}")
        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting historical data import...")
    
    # Initialize InfluxDB client
    client = create_influx_client()
    
    # Import the data
    import_historical_data(client, config['paths']['data_dir'])
    
    logger.info("Historical data import completed")