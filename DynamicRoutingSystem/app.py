from flask import Flask, render_template, request, jsonify
import requests
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# API Keys (Replace with actual keys where required)
AQICN_API_KEY = "7e9e606a54ec17e027ecd3e03d142b5dc87e53d2"

# Base URLs for APIs
OSRM_BASE_URL = "http://router.project-osrm.org"
AQICN_BASE_URL = "https://api.waqi.info"

# Twilio Credentials
TWILIO_ACCOUNT_SID = "AC33778d34ba4df1459eed41e5a0748768"
TWILIO_AUTH_TOKEN = "9f06bc234739fe284c9117c86a60e88b"
TWILIO_PHONE_NUMBER = "+919962610055"

# Email Credentials
EMAIL_ADDRESS = "sampletestproject0307@gmail.com"
EMAIL_PASSWORD = "tqjt jwkz glmd hlyk"  

# Emission factors (kg CO2 per km per vehicle type)
EMISSION_FACTORS = {
    "car": 0.12,  # Example emission factor
    "van": 0.25,
    "truck": 0.5
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    start = request.form['start']
    end = request.form['end']
    vehicle_type = request.form['vehicle_type']
    
    # Step 1: Get route data from OSRM
    route_url = f"{OSRM_BASE_URL}/route/v1/driving/{start};{end}?overview=full&steps=true"
    
    try:
        route_response = requests.get(route_url)
        route_response.raise_for_status()  # Raise an error for bad HTTP responses (4xx or 5xx)
        route_data = route_response.json()
        
        if 'routes' not in route_data:
            return jsonify({"error": "Unable to fetch route. Check inputs."})
        
        route = route_data['routes'][0]
        distance_km = route['distance'] / 1000  # Convert meters to kilometers
        duration_sec = route['duration']  # Seconds
        try:
            steps = [step['maneuver']['instruction'] for leg in route['legs'] for step in leg['steps']]
        except KeyError as e:
            print(f"KeyError encountered: {e}")
            steps = ["Error: Could not retrieve instructions."]
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Route data fetch failed: {e}"})

    # Step 2: Calculate emissions
    emission_rate = EMISSION_FACTORS.get(vehicle_type.lower(), 0.12)  # Default to car if unknown
    total_emissions = distance_km * emission_rate

    # Step 3: Get air quality data
    latitude, longitude = end.split(',')
    air_quality_url = f"{AQICN_BASE_URL}/feed/geo:{latitude};{longitude}/?token={AQICN_API_KEY}"

    print(f"Air Quality URL: {air_quality_url}")  # Log the URL to check if it's correct

    try:
        air_quality_response = requests.get(air_quality_url)
        air_quality_response.raise_for_status()  # Raise an error for bad HTTP responses
        air_quality_data = air_quality_response.json()

        if air_quality_data.get('status') != 'ok':
            return jsonify({"error": "Unable to fetch air quality data."})

        air_quality_index = air_quality_data['data']['aqi']
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Air quality data fetch failed: {e}"})

    # Step 4: Compare emissions with air quality
    travel_decision = "Allowed"
    if total_emissions > air_quality_index:
        travel_decision = "Not Recommended"
        notify_company(start, end, total_emissions, air_quality_index)

    # Response data
    result = {
        "distance_km": distance_km,
        "duration_min": duration_sec / 60,  # Convert seconds to minutes
        "steps": steps,
        "emissions_kg": total_emissions,
        "air_quality_index": air_quality_index,
        "travel_decision": travel_decision
    }
    
    return jsonify(result)

def notify_company(start, end, emissions, air_quality):
    print(f"Notifying company for start: {start}, end: {end}, emissions: {emissions}, air quality: {air_quality}")
    # Email Notification
    send_email_notification(
        subject="High Emissions Alert",
        body=(f"Travel from {start} to {end} has emissions of {emissions:.2f} kg CO2, "
              f"exceeding the air quality index of {air_quality}. Travel is not recommended."),
        recipient_email="sampletestproject0307@gmail.com"
        
    )
    # SMS Notification
    send_sms_notification(
        message=(f"High Emissions Alert: Travel from {start} to {end} has emissions of "
                 f"{emissions:.2f} kg CO2, exceeding air quality index {air_quality}. Travel not recommended."),
        recipient_phone="+919962610055"
    )

def send_email_notification(subject, body, recipient_email):
    try:
        # Create the email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Connect to the server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.set_debuglevel(1)  # Enable debug logs
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)  # Use App Password
        server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())
        server.quit()
        print(f"Email sent successfully to {recipient_email}")
    except smtplib.SMTPAuthenticationError as auth_error:
        print(f"SMTP Authentication Error: {auth_error}")
    except smtplib.SMTPException as smtp_error:
        print(f"SMTP Error: {smtp_error}")
    except Exception as e:
        print(f"General Error sending email: {e}")

def send_sms_notification(message, recipient_phone):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        sms = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=recipient_phone
        )
        print(f"SMS sent successfully: {sms.sid}")
    except Exception as e:
        print(f"Error sending SMS: {e}")
if __name__ == "__main__":
    send_email_notification(
        subject="Test Email",
        body="This is a test email.",
        recipient_email="sampletestproject0307@gmail.com"
    )
if __name__ == '__main__':#to test if the email is being sent if the emissions are high
    notify_company(
        start="77.5946,12.9716",
        end="77.6183,12.9341",
        emissions=150,  # Simulated high emissions
        air_quality=100  # Simulated lower air quality index
    )

if __name__ == '__main__':
    app.run(debug=True)
