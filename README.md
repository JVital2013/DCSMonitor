# DCS Monitor

DCS Monitor is a collection of python scripts that take GOES-R DCS data processed by SatDump, and stores it in an InfluxDB database for easy visualization with Grafana.

IMAGE HERE

## Setup instructions

Setup can be broken down into 5 steps:

1. Configure SatDump
2. Install Docker
3. Set up InfluxDB docker container
4. Set up Grafana docker container
5. Configure DCS Monitor

### SatDump configuration

First, you need to install SatDump and configure it to parse DCS data from GOES-R HRIT. If you are using the GUI, check "Parse DCS". If you're using the command line, add `--parse_dcs` to the command line options.

IMAGE HERE

There are tens of thousands of Data Collection Platforms (DCPs) around the world. To avoid processing too much data, it is highly recommended that you filter DCS messages to those you are interested in. If you are in the United States or Canada, go to [https://hads.ncep.noaa.gov/maps/](https://hads.ncep.noaa.gov/maps/) and find DCPs near you.

IMAGE HERE

The NESDIS ID is the address used on the GOES downlink. Create a comma-seperated list of all DCPs you are interested in, and specify them in the SatDump UI as shown above, or by the `--tracked_addresses` command line parameter. Once you start decoding, you should get a DCS folder in your output directory that contains json files. If you're only tracking a few addresses, it may take several hours for data to appear.

IMAGE HERE

### Install Docker

To run the necessary services, Docker is recommended. If you do not already have docker, follow the instructions [here](https://docs.docker.com/engine/install/debian/). As a note, docker and its containers do not need to be on the same machine running SatDump.

### Set up InfluxDB

Now, let's get the database configured. If you already have InfluxDB running elsewhere, you can re-use that instance with a new bucket/API key. Otherwise, run the following commands on the computer hosting Docker:

```
sudo mkdir /var/lib/influxdb2
sudo docker run -d -p 8086:8086 --name influxdb -v /var/lib/influxdb2:/var/lib/influxdb2 influxdb:latest
```

Once the container starts, go to http://<ip-of-docker-host>:8086/ in your web browser. Follow the setup steps, then do quickstart to get started. Now, let's set up a bucket to store the data, along with an API key. On the left, choose Load Data > Buckets, then choose Create Bucket.

IMAGE HERE

Give it a name like `dcs_data`, and set the retention policy as you like. I recommend "never".

IMAGE HERE

Next, go to Load Data > API Tokens on the left. Select "Generate API token", followed by "Custom API Token"

IMAGE HERE

Give your new token a name, then check both "Read" and "Write" next to the bucket you created. Finally, click "Generate"

IMAGE HERE

You will be shown your API token. Copy the token and keep it somewhere safe for now.

### Install Grafana

Next, let's configure Grafana to visualize the data. Like InfluxDB, you can re-use an existing instance if you already have one. Otherwise, set one up with these steps:

```
sudo mkdir /var/lib/grafana
sudo mkdir /var/lib/grafana/data
sudo mkdir /var/lib/grafana/certs
sudo docker run -d -p 3000:3000 --name grafana --user root -v /var/lib/grafana/data:/var/lib/grafana -v /var/lib/grafana/certs:/certs grafana/grafana-oss
```

Once the container starts, go to http://<ip-of-docker-host>:3000/ and log in with the default admin:admin credentials. Next, go to Connections > Add new connection on the left, and add a new InfluxDB data source.

IMAGE HERE

Configure the connection as follows:

 - Query Language: InfluxQL
 - URL: http://<ip-of-docker-host>:8086/
 - Database: The bucket name set up under InfluxDB; usually dcs_data
 - User: The API token created for the DCS data bucket
 - Password: The API token created for the DCS data bucket

Click Save and Test. If everything is working, you'll get a success message.

IMAGE HERE

### Configure DCS Monitor

Now, let's get data flowing! On the same machine running SatDump, run the following commands:

```
sudo apt install python3-watcher python3-influxdb git
git clone https://github.com/JVital2013/DCSMonitor
cd DCSMonitor
```

In the DCSMonitor directory, edit config.ini and update the following values:

 - host: The IP address running the InfluxDB container
 - port: The port used for InfluxDB. Usually 8086
 - token: The API token generated for your InfluxDB bucket
 - org: The organization name created in InfluxDB
 - bucket: The name of the bucket created to store DCS data
 - data_dir: The full path name where SatDump is storing DCS data

Once configured, run `python3 DCSImport.py` once to load historical data already saved to your drive. If there are errors, work them out before proceeding. When you have successfully imported historical data, run the following command to install a service that sends data to the InfluxDB database as it is processed:

```
./install.sh
```

After this, you can delete the folder you cloned from git. The service will operate under /opt/dcs.

## Building Grafana Dashboards

Congrats! You are now logging DCS data to InfluxDB. Now, let's make a dashboard in Grafana to display your data. Go back to http://<ip-of-docker-host>:3000/ and go to Dashboards on the left. Create a new dashboard.

IMAGE HERE

Click "Add Visualization"

Select the InfluxDB data source you configured when setting up Grafana

IMAGE HERE

At the bottom, click the pencil to allow creating custom queries

IMAGE HERE

From here, the sky's the limit. Below are some sample queries that can display different types of DCS data.

### Display multiple river stages in the same chart

Query:
```
SELECT "value" 
FROM "Height, river stage (FT, M)" 
WHERE $timeFilter 
AND value != 0 
AND ("station" = 'CONESTOGA RIVER NEAR CONESTOGA 1W' 
OR "station" = 'CONESTOGA RIVER NEAR LANCASTER 2ENE') 
GROUP BY "station"
```

Transformation: Rename fields by Regex
 - Match: `^.*{ station: (.*) }$`
 - Replace: `$1`

### Display all battery levels

Query:
```
SELECT "value" 
FROM "Voltage - battery (volt)" 
WHERE $timeFilter 
GROUP BY "station"
```

Transformation: Rename fields by Regex
 - Match: `^.*{ station: (.*) }$`
 - Replace: `$1`

## About
2025 Jamie Vital. Licensed under GPLv3 License