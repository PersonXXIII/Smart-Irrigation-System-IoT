import network
from machine import I2C, Pin, ADC, SoftI2C
import dht
import time
import urequests
from lcd_api import LcdApi
from i2c_lcd import I2cLcd

# Initialize DHT22 on GPIO 32
sensor = dht.DHT22(Pin(32))

# Initialize ADC on GPIO pins for sensors
analog_sensor = ADC(Pin(33))
analog_sensor1 = ADC(Pin(34))
analog_sensor2 = ADC(Pin(35))

# Relays
relay = Pin(2, Pin.OUT)
relay1 = Pin(15, Pin.OUT)

# Display
I2C_ADDR = 0x27
totalRows = 2
totalColumns = 16
i2c = SoftI2C(scl=Pin(16), sda=Pin(4), freq=10000) #initializing the I2C method for ESP32
lcd = I2cLcd(i2c, I2C_ADDR, totalRows, totalColumns)

# LCD
lcd.putstr("Hello!")
time.sleep(2)
lcd.clear()
lcd.putstr("Welcome to Smart Irrigation!")
time.sleep(2)
lcd.clear()
lcd.putstr("Starting...")
time.sleep(2)


# WiFi settings
SSID = 'Wokwi-GUEST'
PASSWORD = ''

# Function to connect to WiFi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        lcd.clear()
        lcd.putstr("Connecting to the WIFI....")
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            pass
    print('Connected to WiFi')
    lcd.clear()
    lcd.putstr("Connected to WIFI....")
    time.sleep(2)
    lcd.clear()
    lcd.putstr("Getting Ready...")
    time.sleep(2)

    print('IP address:', wlan.ifconfig()[0])

# Connect to WiFi
connect_wifi()

# API URL
API_URL = "https://www.api.abe27.site/predict"

# Send data to the API and receive response
def send_data_to_api(temperature, moisture, pressure, altitude):

    # LCD
    lcd.clear()
    lcd.putstr("Analysing...")
    time.sleep(2)

    headers = {'Content-Type': 'application/json'}
    # Create the JSON payload
    payload = {
        "temperature": temperature,
        "soil_moisture": moisture,
        "pressure": pressure,
        "altitude": altitude
    }

    # Send POST request to API
    try:
        response = urequests.post(API_URL, json=payload, headers=headers)
        predicted_class = response.json().get('predicted_class', 'No prediction available')  # Extract prediction
        response.close()  # Always close the response

        # LCD
        lcd.clear()
        lcd.putstr("Updating...")
        time.sleep(2)

        return predicted_class  # Return the predicted class
    except Exception as e:
        print("Error sending data to API:", e)
        return None  # Return None if an error occurs

while True:
    try:
        # Trigger DHT22 reading
        sensor.measure()
        temperature = sensor.temperature()
        
        # Read sensor data
        raw_value = analog_sensor.read()
        raw_value1 = analog_sensor1.read()
        raw_value2 = analog_sensor2.read()

        # Map pressure sensor value to range
        mapped_value = raw_value1 * 10

        # Print results
        print("=================================")
        print("Temperature:", temperature, "°C")
        print(f"Moisture (raw value):", raw_value)
        print(f"Pressure (mapped value):", mapped_value)
        print(f"Altitude (raw value):", raw_value2)

        # Send data to API
        predicted_class = send_data_to_api(temperature, raw_value, mapped_value, raw_value2)
        print(predicted_class)

        print("Sending Data to Website..")
        headers = {'Content-Type': 'application/json'}
        payload1 = {
            "temperature": temperature,
            "soil_moisture": raw_value,
            "pressure": mapped_value,
            "altitude": raw_value2,
            "predicted_class": predicted_class
        }
        WEBSITE_URL = 'https://site.abe27.site/update_data'
        response_to_ui = urequests.post(WEBSITE_URL, json=payload1, headers=headers)
        print(f"{payload1} Data Sent to Website.")

        # LCD
        lcd.clear()
        lcd.putstr(f"Status: {predicted_class}")
        time.sleep(2)

        if predicted_class in ["Dry", "Very Dry"]:
            relay.value(1)
            relay1.value(0)
            lcd.clear()
            lcd.putstr("Water Pump is ON.")
            time.sleep(2)

        elif predicted_class in ["Wet", "Very Wet"]:
            relay.value(0)
            relay1.value(1)
            lcd.clear()
            lcd.putstr("Water Pump is OFF.")
            time.sleep(2)
        else:
            relay.value(0)
            relay1.value(0)

    except OSError as e:
        print("Failed to read from DHT22 sensor:", e)
    
    time.sleep(4)  # Delay to avoid flooding the API
