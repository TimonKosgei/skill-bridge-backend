from models import Badge, UserBadge, db
from datetime import datetime

def check_and_award_badges(user):
    badges = Badge.query.all()
    awarded_badges = []

    for badge in badges:
        # Skip if user already has the badge
        if UserBadge.query.filter_by(user_id=user.user_id, badge_id=badge.badge_id).first():
            continue

        # Check criteria based on badge type
        #doing
        if badge.criteria_type == "video_watched":
            if user.lesson_progress and any(lesson.is_completed for lesson in user.lesson_progress):
                awarded_badges.append(badge)

        elif badge.criteria_type == "module_completed":
            if user.enrollments and any(enrollment.is_completed for enrollment in user.enrollments):
                awarded_badges.append(badge)
        elif badge.criteria_type == "question_asked": #started discussion
            if hasattr(user, 'discussions') and user.discussions:
                awarded_badges.append(badge)
        elif badge.criteria_type == "discussion_participated": #participated in discussion
            if hasattr(user, 'comments') and user.comments:
                awarded_badges.append(badge)
        '''elif badge.criteria_type == "login_streak":
            if hasattr(user, 'login_streak') and user.login_streak >= int(badge.criteria_value):
                awarded_badges.append(badge)
        elif badge.criteria_type == "night_activity":
            if hasattr(user, 'has_watched_after_midnight') and user.has_watched_after_midnight:
            awarded_badges.append(badge)
        elif badge.criteria_type == "videos_completed":
            if hasattr(user, 'videos_completed_count') and user.videos_completed_count >= int(badge.criteria_value):
            awarded_badges.append(badge)
        elif badge.criteria_type == "course_completed":
            if hasattr(user, 'courses_completed_count') and user.courses_completed_count >= int(badge.criteria_value):
            awarded_badges.append(badge)
        
        elif badge.criteria_type == "question_answered":
            if hasattr(user, 'questions_answered_count') and user.questions_answered_count >= int(badge.criteria_value):
            awarded_badges.append(badge)
        elif badge.criteria_type == "minutes_watched":
            if hasattr(user, 'total_minutes_watched') and user.total_minutes_watched >= int(badge.criteria_value):
            awarded_badges.append(badge)
        elif badge.criteria_type == "level_reached":
            if hasattr(user, 'level') and user.level >= int(badge.criteria_value):
            awarded_badges.append(badge)'''

    # Award new badges
    for badge in awarded_badges:
        new_user_badge = UserBadge(
            user_id=user.user_id,
            badge_id=badge.badge_id,
            earned_date =datetime.utcnow()
        )
        db.session.add(new_user_badge)
        print(f"Awarded badge: {badge.name} to {user.username}")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error awarding badges: {e}")
