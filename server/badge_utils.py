from models import Badge, UserBadge, db, User
from datetime import datetime
from email_utils import send_email
from sqlalchemy.exc import IntegrityError

def check_and_award_badges(user):
    # Start a new transaction
    try:
        badges = Badge.query.all()
        awarded_badges = []

        # Get all existing badges for this user
        existing_badges = {ub.badge_id for ub in UserBadge.query.filter_by(user_id=user.user_id).all()}

        for badge in badges:
            # Skip if user already has the badge
            if badge.badge_id in existing_badges:
                continue

            # Check criteria based on badge type
            should_award = False
            
            if badge.criteria_type == "video_watched":
                if user.lesson_progress and any(lesson.is_completed for lesson in user.lesson_progress):
                    should_award = True

            elif badge.criteria_type == "module_completed":
                if user.enrollments and any(enrollment.is_completed for enrollment in user.enrollments):
                    should_award = True
            elif badge.criteria_type == "question_asked": #started discussion
                if hasattr(user, 'discussions') and user.discussions:
                    should_award = True
            elif badge.criteria_type == "discussion_participated": #participated in discussion
                if hasattr(user, 'comments') and user.comments:
                    should_award = True
            elif badge.criteria_type == "login_streak":
                if hasattr(user, 'login_streak') and user.login_streak >= int(badge.criteria_value):
                    should_award = True
            elif badge.criteria_type == "night_activity":
                if hasattr(user, 'has_watched_after_midnight') and user.has_watched_after_midnight:
                    should_award = True
            elif badge.criteria_type == "videos_completed":
                if hasattr(user, 'videos_completed_count') and user.videos_completed_count >= int(badge.criteria_value):
                    should_award = True
            elif badge.criteria_type == "course_completed":
                if hasattr(user, 'courses_completed_count') and user.courses_completed_count >= int(badge.criteria_value):
                    should_award = True
            elif badge.criteria_type == "question_answered":
                if hasattr(user, 'questions_answered_count') and user.questions_answered_count >= int(badge.criteria_value):
                    should_award = True
            elif badge.criteria_type == "minutes_watched":
                if hasattr(user, 'total_minutes_watched') and user.total_minutes_watched >= int(badge.criteria_value):
                    should_award = True
            elif badge.criteria_type == "level_reached":
                if hasattr(user, 'level') and user.level >= int(badge.criteria_value):
                    should_award = True

            if should_award:
                awarded_badges.append(badge)

        # Award new badges
        for badge in awarded_badges:
            try:
                # Double-check that the badge hasn't been awarded in the meantime
                if not UserBadge.query.filter_by(user_id=user.user_id, badge_id=badge.badge_id).first():
                    new_user_badge = UserBadge(
                        user_id=user.user_id,
                        badge_id=badge.badge_id,
                        earned_date=datetime.utcnow()
                    )
                    db.session.add(new_user_badge)
                    print(f"Awarded badge: {badge.name} to {user.username}")

                    # Send email notification
                    subject = f"🎉 New Badge Earned: {badge.name}!"
                    body = f"""
                    Congratulations {user.username}!

                    You've earned the {badge.name} badge! 🎉

                    Badge Details:
                    - Name: {badge.name}
                    - Description: {badge.description}
                    - Tier: {badge.tier}
                    - XP Earned: {badge.xp_value}

                    Keep up the great work and continue your learning journey!

                    Best regards,
                    The SkillBridge Team
                    """
                    send_email(subject, user.email, body)
            except IntegrityError:
                # If there's a duplicate key error, just skip this badge
                db.session.rollback()
                continue

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error awarding badges: {e}")
