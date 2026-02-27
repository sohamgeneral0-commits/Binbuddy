import paho.mqtt.client as mqtt
import json
from database import db, Bin

# This is the object app.py is looking for
mqtt_client = mqtt.Client()


def _to_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None

def on_connect(client, userdata, flags, rc):
    print(f"✅ Connected to MQTT Broker with result code {rc}")
    # Subscribe to the topic your Arduino is sending to
    # The '+' is a wildcard for any bin code
    client.subscribe("binbuddy/bins/+/data")

def on_message(client, userdata, msg):
    from app import app # Import inside to avoid circular imports
    with app.app_context():
        try:
            data = json.loads(msg.payload.decode())
            bin_code = data.get('bin_code')
            
            # Find the bin in the database
            bin_entry = Bin.query.filter_by(bin_code=bin_code).first()
            
            if bin_entry:
                # Update data from Arduino
                bin_entry.fill_level = float(data.get('fill_level', 0))
                bin_entry.distance_cm = float(data.get('distance_cm', 0))
                bin_entry.battery_level = float(data.get('battery', 100))
                
                # Update GPS if valid
                lat = _to_float(data.get('latitude', data.get('lat')))
                lng = _to_float(data.get('longitude', data.get('lng', data.get('lon'))))
                if lat is not None and lng is not None and lat != 0.0 and lng != 0.0:
                    bin_entry.latitude = lat
                    bin_entry.longitude = lng

                # Logic to update Status Enum
                if bin_entry.fill_level >= 90:
                    bin_entry.status = 'full'
                elif bin_entry.fill_level >= 50:
                    bin_entry.status = 'half'
                else:
                    bin_entry.status = 'empty'

                bin_entry.last_updated = db.func.now()
                db.session.commit()

                # Fallback display coords from config if DB values are 0/None
                lat_display = bin_entry.latitude
                lng_display = bin_entry.longitude
                if (lat_display in (None, 0.0)) or (lng_display in (None, 0.0)):
                    lat_display = app.config.get('DEFAULT_LATITUDE', lat_display)
                    lng_display = app.config.get('DEFAULT_LONGITUDE', lng_display)

                print(f"📢 Hardware Update: {bin_code} is now {bin_entry.fill_level}% | GPS: (Lat: {lat_display}, Long: {lng_display}) | Battery: {bin_entry.battery_level}%")
            else:
                print(f"⚠️ Warning: Received data for unknown bin code: {bin_code}")
                
        except Exception as e:
            print(f"❌ Error parsing MQTT message: {e}")

# Set the callbacks
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def start_mqtt(app):
    try:
        # Use the broker address from your config
        broker = app.config.get('MQTT_BROKER_HOST', 'localhost')
        port = app.config.get('MQTT_BROKER_PORT', 1883)
        mqtt_client.connect(broker, port, 60)
        mqtt_client.loop_start() # Starts the background thread
    except Exception as e:
        print(f"❌ Could not connect to MQTT Broker: {e}")



# import paho.mqtt.client as mqtt
# import json
# from database import db, Bin  # Import existing ones, don't redefine!

# def start_mqtt(app):
#     client = mqtt.Client()

#     def on_message(client, userdata, msg):
#         with app.app_context():
#             try:
#                 data = json.loads(msg.payload.decode())
#                 bin_code = data.get('bin_code')
#                 # If sensor sends distance_cm
#                 dist = float(data.get('distance_cm', 0))
                
#                 b = Bin.query.filter_by(bin_code=bin_code).first()
#                 if b:
#                     # LOGIC: Fill level based on distance
#                     # If bin is 22cm deep and trash is 2cm away, it's 90% full
#                     capacity = b.capacity_cm if b.capacity_cm > 0 else 22
#                     fill = max(0, min(100, ((capacity - dist) / capacity) * 100))
                    
#                     b.fill_level = round(fill, 2)
#                     b.distance_cm = dist
#                     b.battery_level = float(data.get('battery', 100))
                    
#                     # Update status enum
#                     if fill >= 90: b.status = 'full'
#                     elif fill >= 50: b.status = 'half'
#                     else: b.status = 'empty'
                    
#                     db.session.commit()
#                     print(f"MQTT: Updated {bin_code} to {fill}%")
#             except Exception as e:
#                 print(f"MQTT Error: {e}")

#     client.on_message = on_message
#     client.connect("localhost", 1883)
#     client.subscribe("binbuddy/updates")
#     client.loop_start()

# """
# BinBuddy MQTT Handler
# Subscribes to sensor topics and updates the database in real-time.

# Topic structure:
#   binbuddy/bins/{bin_code}/data      ← sensor publishes fill level
#   binbuddy/bins/{bin_code}/status    ← device heartbeat / status
#   binbuddy/alerts/{bin_code}         ← high-priority alerts
# """
# import json
# import logging
# from datetime import datetime
# import paho.mqtt.client as mqtt
# from config import Config

# logger = logging.getLogger(__name__)

# # Global MQTT client (accessible from Flask routes if needed)
# mqtt_client = mqtt.Client(client_id="binbuddy-backend")

# def _on_connect(client, userdata, flags, rc):
#     if rc == 0:
#         logger.info("Connection: MQTT connected to broker")
#         # Subscribe to all bin data topics
#         client.subscribe(f"{Config.MQTT_TOPIC_BASE}/bins/+/data")
#         client.subscribe(f"{Config.MQTT_TOPIC_BASE}/bins/+/status")
#         client.subscribe(f"{Config.MQTT_TOPIC_BASE}/alerts/#")
#     else:
#         logger.error(f"ERR: MQTT connection failed, code {rc}")

# def _on_message(client, userdata, msg):
#     """
#     Process incoming MQTT message from IoT sensor.
#     Expected JSON payload from ESP8266/ESP32:
#     {
#       "bin_code": "BIN-W01-001",
#       "fill_level": 75.5,
#       "battery": 88.0,
#       "distance_cm": 25.0,
#       "timestamp": 1700000000
#     }
#     """
#     app = userdata  # Flask app passed as userdata
#     try:
#         payload = json.loads(msg.payload.decode('utf-8'))
#         topic   = msg.topic
#         logger.info(f"\nMQTT message on {topic}: {payload}")

#         with app.app_context():
#             from database import db, Bin, Notification

#             bin_code   = payload.get('bin_code')
#             fill_level = float(payload.get('fill_level', 0))
#             battery    = float(payload.get('battery', 100))
#             distance   = float(payload.get('distance_cm', 0))   # ← ADDed THIS LINE
#             latitude  = float(payload.get('latitude', 0))
#             longitude = float(payload.get('longitude', 0))

#             if not bin_code:
#                 logger.warning("MQTT payload missing bin_code")
#                 return

#             the_bin = Bin.query.filter_by(bin_code=bin_code).first()
#             if not the_bin:
#                 logger.warning(f"Bin not found: {bin_code}")
#                 return

#             # Update fill level
#             # the_bin.fill_level    = round(fill_level, 2)
#             # the_bin.battery_level = round(battery, 2)
#             # the_bin.last_updated  = datetime.utcnow()
#             # FIXED
#             the_bin.fill_level    = round(fill_level, 2)
#             the_bin.battery_level = round(battery, 2)
#             the_bin.distance_cm   = round(distance, 2)        # ← ADD THIS
#             #GPS
#             the_bin.latitude  = latitude
#             the_bin.longitude = longitude
#             the_bin.last_updated  = datetime.utcnow()
#             logger.info(f"{bin_code} → Fill: {fill_level:.1f}%  Dist: {distance:.1f}cm")
#             logger.info(f"GPS → Lat: {latitude} | Lon: {longitude}")

#             # Determine status
#             if fill_level >= 80:
#                 the_bin.status = 'full'
#                 # Create alert notification
#                 notif = Notification(
#                     title   = f"Bin {bin_code} is FULL",
#                     message = f"Bin at {the_bin.location_name} has reached {fill_level:.0f}% capacity.",
#                     type    = 'alert'
#                 )
#                 db.session.add(notif)
#             elif fill_level >= 50:
#                 the_bin.status = 'half'
#             else:
#                 the_bin.status = 'empty'

#             db.session.commit()
#             logger.info(f"Updated bin {bin_code}: {fill_level}%")
#             logger.info(f"DB saved — {bin_code}: {fill_level:.1f}% | status: {the_bin.status}")


#     except Exception as e:
#         logger.exception(f"Error processing MQTT message: {e}")

# def _on_disconnect(client, userdata, rc):
#     logger.warning(f"MQTT disconnected (rc={rc}). Will auto-reconnect...")

# def start_mqtt(app):
#     """Start MQTT client loop — call this in a daemon thread."""
#     mqtt_client.on_connect    = _on_connect
#     mqtt_client.on_message    = _on_message
#     mqtt_client.on_disconnect = _on_disconnect
#     mqtt_client.user_data_set(app)          # pass Flask app for DB access
    

#     try:
#         mqtt_client.connect(
#             Config.MQTT_BROKER_HOST,
#             Config.MQTT_BROKER_PORT,
#             Config.MQTT_KEEPALIVE
#         )
#         mqtt_client.loop_forever(retry_first_connection=True)
#     except Exception as e:
#         logger.error(f"MQTT start error: {e}")
