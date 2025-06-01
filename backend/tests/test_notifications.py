#!/usr/bin/env python3
"""
Test script to debug notification system issues
"""

import asyncio
import logging
from app.core.database import get_database
from app.services.user_service import user_service
from app.services.ticket_service import ticket_service
from app.services.notification_service import notification_service
from app.schemas.ticket import TicketCreateSchema, TicketUrgency
from app.schemas.user import UserCreateSchema, UserRole

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_notification_system():
    """Test the complete notification flow"""

    print("Testing Notification System...")
    print("=" * 50)

    # 1. Check existing users
    print("\n1. Checking existing users...")
    db = get_database()
    if db is None:
        print("Database connection failed!")
        return

    users = await db.users.find({}).to_list(length=100)
    print(f"Found {len(users)} total users:")
    for user in users:
        print(f"  - {user.get('username', 'N/A')} ({user.get('role', 'N/A')}) - ID: {user.get('_id')}")

    # 2. Check HR agents specifically
    print("\n2. Checking HR agents...")
    hr_agents = await user_service.get_users_by_role('hr_agent')
    print(f"HR agents found: {len(hr_agents)}")
    for agent in hr_agents:
        print(f"  - {agent.username} (ID: {agent._id})")

    # 3. Check IT agents
    print("\n3. Checking IT agents...")
    it_agents = await user_service.get_users_by_role('it_agent')
    print(f"IT agents found: {len(it_agents)}")
    for agent in it_agents:
        print(f"  - {agent.username} (ID: {agent._id})")

    # 4. Check admin users
    print("\n4. Checking admin users...")
    admin_users = await user_service.get_users_by_role('admin')
    print(f"Admin users found: {len(admin_users)}")
    for admin in admin_users:
        print(f"  - {admin.username} (ID: {admin._id})")

    # 5. Check existing notifications
    print("\n5. Checking existing notifications...")
    notifications = await db.notifications.find({}).to_list(length=100)
    print(f"Found {len(notifications)} total notifications:")
    for notif in notifications:
        print(f"  - {notif.get('title', 'N/A')} for user {notif.get('user_id', 'N/A')} (read: {notif.get('read', False)})")

    # 6. Test creating a notification manually
    print("\n6. Testing manual notification creation...")
    if hr_agents:
        test_user_id = str(hr_agents[0]._id)
        notif_id = await notification_service.create_notification(
            user_id=test_user_id,
            title="Test Notification",
            message="This is a test notification to verify the system is working",
            notification_type="system_alert"
        )
        if notif_id:
            print(f"Successfully created test notification: {notif_id}")
        else:
            print("Failed to create test notification")

    # 7. Test ticket creation (if we have a regular user)
    print("\n7. Testing ticket creation...")
    regular_users = await user_service.get_users_by_role('user')
    if regular_users:
        test_user = regular_users[0]
        print(f"Creating test ticket for user: {test_user.username}")

        try:
            ticket_data = TicketCreateSchema(
                title="Test Notification Ticket",
                description="This is a test ticket to verify notifications are working",
                urgency=TicketUrgency.MEDIUM
            )

            created_ticket = await ticket_service.create_ticket(ticket_data, str(test_user._id))
            print(f"Successfully created test ticket: {created_ticket.ticket_id}")

            # Check if notifications were created
            await asyncio.sleep(2)  # Wait a bit for webhook processing
            new_notifications = await db.notifications.find({}).to_list(length=100)
            print(f"Total notifications after ticket creation: {len(new_notifications)}")

        except Exception as e:
            print(f"Failed to create test ticket: {str(e)}")
    else:
        print("No regular users found to test ticket creation")

    print("\n" + "=" * 50)
    print("Notification system test completed!")


if __name__ == "__main__":
    asyncio.run(test_notification_system())
