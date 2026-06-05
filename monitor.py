import board
import adafruit_dht
import json
import logging
import time
import urllib.error
import urllib.request
import RPi.GPIO as GPIO


LOG_FILE = "./data.log"
MOCK_API_URL = "https://unaApi.hipotetica.dev/sensor-data"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Thresholds
TEMP_THRESHOLD = 22  # C
HUMIDITY_THRESHOLD = 55  # % RH

# init dht11 sensor
dht_sensor = adafruit_dht.DHT11(board.D6)


def post_sensor_data(temperature, humidity):
    payload = {
        "temperature": temperature,
        "humidity": humidity,
    }
    request = urllib.request.Request(
        MOCK_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            logger.info("Mock HTTPS POST succeeded with status %s", response.status)
    except urllib.error.URLError as error:
        logger.info("Mock HTTPS POST failed: %s", error)


def threshold_exceeded(temp, humidity):
    logger.warning("Alert: temperature=%s, humidity=%s", temp, humidity)
    post_sensor_data(temp, humidity)
    



def monitor_sensors():
    try:
        while True:
            try:
                # Read DHT11 sensor
                temperature = dht_sensor.temperature
                humidity = dht_sensor.humidity
                
                
                # Print current values
                message = f"Temp: {temperature}C --- Humidity: {humidity}% RH"
                logger.info(message)

                post_sensor_data(temperature, humidity)
                
                # Check thresholds
                if temperature > TEMP_THRESHOLD or humidity > HUMIDITY_THRESHOLD:
                    logger.warning(
                        "Threshold exceeded: temperature=%s, humidity=%s",
                        temperature,
                        humidity,
                    )
                    threshold_exceeded(temperature, humidity)
                
                time.sleep(1)
                
            except RuntimeError as e:
                logger.error("DHT11 Error: %s", e)
                time.sleep(2)
                
    except KeyboardInterrupt:
        print("Unexpected interruption. Exiting program...")
    finally:
        dht_sensor.exit()
        GPIO.cleanup()

if __name__ == "__main__":
    monitor_sensors()
