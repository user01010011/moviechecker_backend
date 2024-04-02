from flask import Flask, request, jsonify
import os 
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta 
import smtplib 
from email.mime.text import MIMEText 
from email.mime.multipart import MIMEMultipart
import requests 
from dotenv import load_dotenv

# Load environment variables 
load_dotenv()

# Environment variables 
DATABASE_URL = os.environ['DATABASE_URL']
SENDER_EMAIL = os.environ['SENDER_EMAIL']
EMAIL_PASSWORD = os.environ['EMAIL_PASSWORD']

app = Flask(__name__)

def connect_to_db(): 
    conn = psycopg2.connect(DATABASE_URL)
    return conn 

def notification_already_sent(date): 
    with connect_to_db() as conn: 
        with conn.cursor(cursor_factory=RealDictCursor) as cursor: 
            cursor.execute('SELECT sent FROM notifications WHERE notification_date = %s', (date,))
            result = cursor.fetchone()
            return result is not None and result['sent']

def mark_notification_as_sent(date): 
    with connect_to_db() as conn: 
        with conn.cursor() as cursor: 
            cursor.execute('INSERT INTO notifications (notification_date, sent) VALUES (%s, TRUE) ON CONFLICT (notification_date) DO UPDATE SET sent = TRUE', (date,))
            conn.commit()

def send_email_notification(date, url, receiver_email): 
    message = MIMEMultipart("alternative")
    message["Subject"] = f"IMAX Show Open for Booking on {date}"
    message["From"] = SENDER_EMAIL 
    message["To"] = receiver_email # Using the receiver_email parameter 

    # Text and HTML versions of the message
    text = f"IMAX show for AMC Dune Part Two is open on {date} at AMC Orange 30! Go grab your seat! Check it out here: {url}"
    html = f"""\
    <html>
      <body>
        <p>IMAX show for <strong>AMC Dune Part Two</strong> is open on {date} at AMC Orange 30! Go grab your seat!<br>
           Check it out <a href="{url}">here</a>.
        </p>
      </body>
    </html>
    """
    
    # Attach both the plain text and the HTML part to the message
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)

    # Send the email 
    try: 
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465) # Assuming you are using Gmail's SMTP server
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, message.as_string())
        server.quit()
        print(f"Email sent fro {date}.")
    except Exception as e: 
        print(f"Failed to send email: {e}")

def generate_date_range(start_date, end_date): 
    for n in range(int((end_date - start_date).days) + 1): 
        yield start_date + timedelta(n)

@app.route('/check_showtimes', methods=['POST'])
def check_showtimes_for_range(): 
    data = request.json 
    start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
    end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
    movie_id = data['movie_id']
    theater_id_ = data['theater_id']
    receiver_email = data['receiver_email']

    for single_date in generate_date_range(start_date, end_date):
        formatted_date = single_date.strftime('%Y-%m-%d')
        if notification_already_sent(formatted_date): 
            continue 

        url = f'https://www.amctheatres.com/movies/{movie_id}/showtimes/{movie_id}/{formatted_date}/{theater_id}/all'
        response = requests.get(url)

        if response.status_code == 200 and 'No Showtimes on This Date' not in response.text: 
            send_email_notification(formatted_date, url, receiver_email)
            mark_notification_as_sent(formatted_date)

    return jsonify({"message": "Showtime checks completed."})

if __name__ == '__main__': 
    app.run(debut=True)






