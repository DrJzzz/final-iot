import board
import adafruit_dht
import json
import logging
import time
import urllib.error
import urllib.request
import RPi.GPIO as GPIO


LOG_FILE = "/opt/monitor/data.log"
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

# Anomaly detection
MIN_VALID_TEMP = 0
MAX_VALID_TEMP = 50
MIN_VALID_HUMIDITY = 0
MAX_VALID_HUMIDITY = 90
MAX_TEMP_JUMP_PER_SEC = 8
MAX_HUMIDITY_JUMP_PER_SEC = 10
MAX_STUCK_REPEATS = 100
MAX_CONSECUTIVE_READ_ERRORS = 5

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


def post_anomaly_event(reason, temperature=None, humidity=None):
    payload = {
        "event": "sensor_anomaly",
        "reason": reason,
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
            logger.warning("Anomaly event posted with status %s", response.status)
    except urllib.error.URLError as error:
        logger.warning("Anomaly event post failed: %s", error)


def flag_sensor_malfunction(reason, temperature=None, humidity=None):
    logger.error(
        "Sensor malfunction suspected: %s (temperature=%s, humidity=%s)",
        reason,
        temperature,
        humidity,
    )
    post_anomaly_event(reason, temperature, humidity)


def detect_sensor_anomaly(temperature, humidity, detector_state):
    if temperature is None or humidity is None:
        return "missing reading"

    if not (MIN_VALID_TEMP <= temperature <= MAX_VALID_TEMP):
        return "temperature out of valid DHT11 range"

    if not (MIN_VALID_HUMIDITY <= humidity <= MAX_VALID_HUMIDITY):
        return "humidity out of valid range"

    now = time.time()
    last_temp = detector_state["last_temp"]
    last_humidity = detector_state["last_humidity"]
    last_time = detector_state["last_time"]

    if last_temp is not None and last_humidity is not None and last_time is not None:
        elapsed = max(now - last_time, 1e-6)
        temp_jump_rate = abs(temperature - last_temp) / elapsed
        humidity_jump_rate = abs(humidity - last_humidity) / elapsed

        if temp_jump_rate > MAX_TEMP_JUMP_PER_SEC:
            return "temperature jumped too fast"

        if humidity_jump_rate > MAX_HUMIDITY_JUMP_PER_SEC:
            return "humidity jumped too fast"

        if temperature == last_temp and humidity == last_humidity:
            detector_state["stuck_repeats"] += 1
            if detector_state["stuck_repeats"] >= MAX_STUCK_REPEATS:
                return "reading appears stuck"
        else:
            detector_state["stuck_repeats"] = 0

    detector_state["last_temp"] = temperature
    detector_state["last_humidity"] = humidity
    detector_state["last_time"] = now
    return None


def threshold_exceeded(temp, humidity):
    logger.warning("Alert: temperature=%s, humidity=%s", temp, humidity)
    post_sensor_data(temp, humidity)
    



def monitor_sensors():
    detector_state = {
        "last_temp": None,
        "last_humidity": None,
        "last_time": None,
        "stuck_repeats": 0,
        "read_error_count": 0,
    }

    try:
        while True:
            try:
                # Read DHT11 sensor
                temperature = dht_sensor.temperature
                humidity = dht_sensor.humidity

                detector_state["read_error_count"] = 0
                
                
                
                # Print current values
                message = f"Temp: {temperature}C --- Humidity: {humidity}% RH"
                logger.info(message)

                anomaly_reason = detect_sensor_anomaly(temperature, humidity, detector_state)
                if anomaly_reason:
                    flag_sensor_malfunction(anomaly_reason, temperature, humidity)

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
                detector_state["read_error_count"] += 1
                if detector_state["read_error_count"] >= MAX_CONSECUTIVE_READ_ERRORS:
                    flag_sensor_malfunction(
                        "too many consecutive DHT11 read errors",
                        detector_state["last_temp"],
                        detector_state["last_humidity"],
                    )
                    detector_state["read_error_count"] = 0
                time.sleep(2)
                
    except KeyboardInterrupt:
        print("Unexpected interruption. Exiting program...")
    finally:
        dht_sensor.exit()
        GPIO.cleanup()

if __name__ == "__main__":
    monitor_sensors()
