# moviechecker_backend/check_email.py

import os
import requests
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv()

# Environment variables
DATABASE_URL = os.environ['DATABASE_URL']
SENDER_EMAIL = os.environ['SENDER_EMAIL']
RECEIVER_EMAIL = os.environ['RECEIVER_EMAIL']
EMAIL_PASSWORD = os.environ['EMAIL_PASSWORD']

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

def send_email_notification(date, url):
    message = MIMEMultipart("alternative")
    message["Subject"] = f"IMAX Show Open for Booking on {date}"
    message["From"] = SENDER_EMAIL
    message["To"] = RECEIVER_EMAIL

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
    
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    
    message.attach(part1)
    message.attach(part2)
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message.as_string())
        server.quit()
        print(f"Email sent for {date}.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def generate_date_range(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def check_showtimes_for_range(start_date, end_date):
    for single_date in generate_date_range(start_date, end_date):
        formatted_date = single_date.strftime("%Y-%m-%d")
        if notification_already_sent(formatted_date):
            print(f"Already notified for {formatted_date}.")
            continue

        url = f'https://www.amctheatres.com/movies/dune-part-two-68123/showtimes/dune-part-two-68123/{formatted_date}/amc-orange-30/all'
        response = requests.get(url) # Simplified, use appropriate headers and cookies as needed

        if response.status_code == 200 and 'No Showtimes on This Date' not in response.text:
            send_email_notification(formatted_date, url)
            mark_notification_as_sent(formatted_date)
            print(f"Notified for {formatted_date}.")
        else:
            print(f"No showtimes available for {formatted_date}.")

# Start from today to the next 14 days
start_date = datetime.now()
end_date = start_date + timedelta(days=14)

# Execute the check
check_showtimes_for_range(start_date, end_date)
