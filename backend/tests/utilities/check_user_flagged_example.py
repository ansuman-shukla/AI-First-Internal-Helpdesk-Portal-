#!/usr/bin/env python3
"""
Example: How to Check if a User is Flagged

This script demonstrates different ways to check if a user has been flagged
for attempting to create tickets with inappropriate content.
"""

import asyncio
import requests
import json

# Example API calls to check user flagging status

def check_flagged_users_via_api():
    """Example: Check flagged users via admin API"""
    
    print("🔍 Method 1: Check All Flagged Users")
    print("=" * 40)
    
    # Admin authentication required
    headers = {
        "Authorization": "Bearer YOUR_ADMIN_JWT_TOKEN",
        "Content-Type": "application/json"
    }
    
    # Get all flagged users in last 30 days
    response = requests.get(
        "http://localhost:8000/admin/user-violations/flagged-users?days=30",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        flagged_users = data["flagged_users"]
        
        print(f"📊 Found {len(flagged_users)} flagged users:")
        
        for user in flagged_users:
            print(f"\n👤 User: {user['username']} (ID: {user['user_id']})")
            print(f"   🚨 Risk Level: {user['risk_level']}")
            print(f"   📈 Total Violations: {user['total_violations']}")
            print(f"   🏷️  Violation Types: {', '.join(user['violation_types'])}")
            print(f"   📅 Latest Violation: {user['latest_violation']}")
            print(f"   ⚠️  Unreviewed: {user['unreviewed_count']}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")


def check_specific_user_violations(user_id):
    """Example: Check violations for specific user"""
    
    print(f"\n🔍 Method 2: Check Specific User ({user_id})")
    print("=" * 40)
    
    headers = {
        "Authorization": "Bearer YOUR_ADMIN_JWT_TOKEN",
        "Content-Type": "application/json"
    }
    
    # Get violations for specific user
    response = requests.get(
        f"http://localhost:8000/admin/user-violations/user/{user_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        violations = data["violations"]
        
        print(f"👤 User: {data['username']}")
        print(f"📊 Total Violations: {data['total_count']}")
        
        if violations:
            print("\n📋 Violation Details:")
            for i, violation in enumerate(violations, 1):
                print(f"\n   {i}. {violation['violation_type'].upper()} - {violation['severity'].upper()}")
                print(f"      📅 Date: {violation['created_at']}")
                print(f"      📝 Title: {violation['attempted_title'][:50]}...")
                print(f"      🎯 Confidence: {violation['detection_confidence']:.2f}")
                print(f"      📖 Reason: {violation['detection_reason'][:80]}...")
                print(f"      ✅ Reviewed: {'Yes' if violation['admin_reviewed'] else 'No'}")
        else:
            print("✅ No violations found for this user")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")


# Example using the service directly (for backend code)
async def check_user_flagged_programmatically():
    """Example: Check user flagging programmatically in backend code"""
    
    print("\n🔍 Method 3: Programmatic Check (Backend Code)")
    print("=" * 40)
    
    # Import the service (this would be in your backend code)
    try:
        from app.services.user_violation_service import user_violation_service
        
        # Example user ID
        user_id = "user_id_here"
        
        # Get user violations
        violations = await user_violation_service.get_user_violations(user_id, days=30)
        
        if violations:
            print(f"🚨 User {user_id} is FLAGGED")
            print(f"📊 Total violations in last 30 days: {len(violations)}")
            
            # Calculate risk level
            high_severity_count = sum(1 for v in violations if v.severity in ['high', 'critical'])
            unreviewed_count = sum(1 for v in violations if not v.admin_reviewed)
            
            if len(violations) >= 5 or high_severity_count >= 2:
                risk_level = "CRITICAL"
            elif len(violations) >= 3 or (high_severity_count >= 1 and unreviewed_count > 0):
                risk_level = "HIGH"
            elif len(violations) >= 2 or unreviewed_count > 0:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            print(f"⚠️  Risk Level: {risk_level}")
            
            # Show recent violations
            print("\n📋 Recent Violations:")
            for violation in violations[:3]:  # Show last 3
                print(f"   • {violation.violation_type} ({violation.severity})")
                print(f"     Date: {violation.created_at}")
                print(f"     Content: {violation.attempted_title[:40]}...")
        else:
            print(f"✅ User {user_id} is NOT flagged (no violations found)")
            
    except ImportError:
        print("❌ Cannot import service (not in backend environment)")


def check_user_in_frontend():
    """Example: How to check user flagging in frontend"""

    print("\n🔍 Method 4: Frontend Integration")
    print("=" * 40)

    frontend_code = '''
    // In your React component or admin dashboard

    const checkUserFlagged = async (userId) => {
      try {
        const response = await fetch(`/admin/user-violations/user/${userId}`, {
          headers: {
            'Authorization': `Bearer ${adminToken}`,
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();

          if (data.total_count > 0) {
            console.log(`🚨 User ${data.username} is FLAGGED`);
            console.log(`📊 Total violations: ${data.total_count}`);

            // Show in UI
            setUserStatus({
              flagged: true,
              violationCount: data.total_count,
              violations: data.violations
            });
          } else {
            console.log(`✅ User ${data.username} is NOT flagged`);
            setUserStatus({ flagged: false });
          }
        }
      } catch (error) {
        console.error('Error checking user status:', error);
      }
    };

    // Usage in component
    useEffect(() => {
      if (selectedUserId) {
        checkUserFlagged(selectedUserId);
      }
    }, [selectedUserId]);
    '''

    print(frontend_code)


def main():
    """Main demonstration function"""

    print("🚀 User Flagging Check Examples")
    print("=" * 50)
    print("This demonstrates how to check if users are flagged")
    print("for attempting to create inappropriate content.")
    print()

    # Method 1: API call to get all flagged users
    check_flagged_users_via_api()

    # Method 2: API call for specific user
    check_specific_user_violations("example_user_id")

    # Method 3: Programmatic check (backend)
    # asyncio.run(check_user_flagged_programmatically())

    # Method 4: Frontend integration example
    check_user_in_frontend()

    print("\n" + "=" * 50)
    print("📋 SUMMARY: Ways to Check User Flagging")
    print("=" * 50)
    print("1. 🌐 Admin API: GET /admin/user-violations/flagged-users")
    print("2. 👤 User API: GET /admin/user-violations/user/{user_id}")
    print("3. 🔧 Backend Service: user_violation_service.get_user_violations()")
    print("4. 💻 Frontend: Fetch API calls with admin authentication")
    print()
    print("🔒 All methods require admin authentication!")
    print("✅ System is ready to track inappropriate content attempts!")


if __name__ == "__main__":
    main()
