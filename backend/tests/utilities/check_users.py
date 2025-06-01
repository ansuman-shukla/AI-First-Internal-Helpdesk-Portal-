#!/usr/bin/env python3
"""
Check existing users in the database
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_database
from app.services.user_service import user_service

async def check_users():
    db = get_database()
    users = await db.users.find({}).to_list(length=100)
    print('Existing users:')
    for user in users:
        print(f'  - {user.get("username", "N/A")} ({user.get("role", "N/A")}) - ID: {user.get("_id")}')
    
    # Check HR agents specifically
    hr_agents = await user_service.get_users_by_role('hr_agent')
    print(f'\nHR agents found: {len(hr_agents)}')
    for agent in hr_agents:
        print(f'  - {agent.username} (ID: {agent._id})')
    
    # Check IT agents
    it_agents = await user_service.get_users_by_role('it_agent')
    print(f'\nIT agents found: {len(it_agents)}')
    for agent in it_agents:
        print(f'  - {agent.username} (ID: {agent._id})')

if __name__ == "__main__":
    asyncio.run(check_users())
