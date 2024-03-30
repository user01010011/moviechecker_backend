import os
import requests 
from datetime import datetime, timedelta 
import psycopg2 
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv 

# Load environment variables 
load_dotenv()

# Environment variables
DATABASE_URL = os.environ['DATABASE_URL']
bot_token = os.environ['BOT_TOKEN']
chat_id = os.environ['CHAT_ID']

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

def generate_date_range(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def check_showtimes_for_range(start_date, end_date): 
    for single_date in generate_date_range(start_date, end_date):
        formatted_date = single_date.strftime("%Y-%m-%d")
        if notification_already_sent(formatted_date): 
            print(f"Already notified for {formatted_date}.")
            continue 
        
         # Use the provided URL, adjusting the date dynamically
        url = f'https://www.amctheatres.com/movies/dune-part-two-68123/showtimes/dune-part-two-68123/{formatted_date}/amc-orange-30/all'
        response = requests.get(url) # Simplified, use appropriate headers and cookies as needed

        if response.status.code == 200 and 'No-Showtimes-First' not in response.text: 
            message_text = f'IMAX show for AMC Dune Part Two is open on {formatted_date} at AMC Orange 30! Go grab the seat! {url}'
            telegram_api_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
            params = {'chat_id': chat_id, 'text': message_text}
            requests.posts(telegram_api_url, data=params)
            mark_notification_as_sent(formatted_date)
            print(f"Notified for {formatted_date}.")
        else: 
            print(f"No showtimes available for {formatted_date}.")

# Start from today to the next 14 days
start_date = datetime.now()
end_date = start_date + timedelta(days=14)

# Execute the check
if bot_token and chat_id: 
    check_showtimes_for_range(start_date, end_date)
else: 
    print("Error: Telegram BOT_TOKEN or CHAT_ID environment variable is not set.")


