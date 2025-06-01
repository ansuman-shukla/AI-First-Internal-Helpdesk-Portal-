import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
client = pymongo.MongoClient(os.getenv("MONGODB_URI"))
db = client.helpdesk_db

# Check notifications
notifications = list(db.notifications.find({}))
print(f"Total notifications: {len(notifications)}")

for notif in notifications:
    print(f"- {notif.get('title', 'N/A')} for user {notif.get('user_id', 'N/A')}")

# Check tickets
tickets = list(db.tickets.find({}).sort("created_at", -1).limit(5))
print(f"\nRecent tickets: {len(tickets)}")

for ticket in tickets:
    print(f"- {ticket.get('ticket_id', 'N/A')}: {ticket.get('title', 'N/A')}")

client.close()
