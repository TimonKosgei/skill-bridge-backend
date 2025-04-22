from datetime import datetime
from app import db, app
from models import Badge

def seed_badges():
    badge_data = [
        {
            "emoji": "🎉",
            "name": "First Step",
            "description": "Watched your first video",
            "criteria_type": "video_watched",
            "criteria_value": "1",
            "tier": "bronze",
            "xp_value": 10,
            "is_hidden": False
        },
        {
            "emoji": "📚",
            "name": "Learner Onboarded",
            "description": "Completed your first course/module",
            "criteria_type": "module_completed",
            "criteria_value": "1",
            "tier": "bronze",
            "xp_value": 20,
            "is_hidden": False
        },
        {
            "emoji": "💡",
            "name": "Curious Mind",
            "description": "Asked your first question in the forum/chat",
            "criteria_type": "question_asked",
            "criteria_value": "1",
            "tier": "bronze",
            "xp_value": 15,
            "is_hidden": False
        },
        {
            "emoji": "🔥",
            "name": "Streak Starter",
            "description": "Watched videos 3 days in a row",
            "criteria_type": "login_streak",
            "criteria_value": "3",
            "tier": "silver",
            "xp_value": 30,
            "is_hidden": False
        },
        {
            "emoji": "🐱‍👤",
            "name": "Midnight Coder",
            "description": "Watched a lesson after midnight",
            "criteria_type": "night_activity",
            "criteria_value": "1",
            "tier": "silver",
            "xp_value": 25,
            "is_hidden": False
        },
        {
            "emoji": "🚀",
            "name": "Committed Learner",
            "description": "Logged in 7 days in a row",
            "criteria_type": "login_streak",
            "criteria_value": "7",
            "tier": "silver",
            "xp_value": 50,
            "is_hidden": False
        },
        {
            "emoji": "🧠",
            "name": "Knowledge Seeker",
            "description": "Completed 10 videos",
            "criteria_type": "videos_completed",
            "criteria_value": "10",
            "tier": "silver",
            "xp_value": 40,
            "is_hidden": False
        },
        {
            "emoji": "🥇",
            "name": "Course Champion",
            "description": "Finished an entire course",
            "criteria_type": "course_completed",
            "criteria_value": "1",
            "tier": "gold",
            "xp_value": 100,
            "is_hidden": False
        },
        {
            "emoji": "🗨️",
            "name": "First Talk",
            "description": "Participated in a discussion",
            "criteria_type": "discussion_participated",
            "criteria_value": "1",
            "tier": "bronze",
            "xp_value": 15,
            "is_hidden": False
        },
        {
            "emoji": "🤝",
            "name": "Helper",
            "description": "Answered another student's question",
            "criteria_type": "question_answered",
            "criteria_value": "1",
            "tier": "silver",
            "xp_value": 30,
            "is_hidden": False
        },
        {
            "emoji": "💯",
            "name": "100 Club",
            "description": "Watched 100+ minutes of content",
            "criteria_type": "minutes_watched",
            "criteria_value": "100",
            "tier": "gold",
            "xp_value": 75,
            "is_hidden": False
        },
        {
            "emoji": "📈",
            "name": "Level Up!",
            "description": "Reached level 5 in your learning journey",
            "criteria_type": "level_reached",
            "criteria_value": "5",
            "tier": "gold",
            "xp_value": 150,
            "is_hidden": False
        }
    ]

    # Clear existing badges (optional - be careful with this in production)
    # Badge.query.delete()
    
    for data in badge_data:
        # Check if badge already exists
        if not Badge.query.filter_by(name=data['name']).first():
            badge = Badge(
                emoji=data['emoji'],
                name=data['name'],
                description=data['description'],
                criteria_type=data['criteria_type'],
                criteria_value=data['criteria_value'],
                tier=data['tier'],
                xp_value=data['xp_value'],
                is_hidden=data['is_hidden'],
                created_date=datetime.utcnow()
            )
            db.session.add(badge)
    
    try:
        db.session.commit()
        print("Successfully seeded badges!")
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding badges: {e}")

if __name__ == '__main__':
    with app.app_context():
        seed_badges()