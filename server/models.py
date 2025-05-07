from database import db
from datetime import datetime
from sqlalchemy_serializer import SerializerMixin


class User(db.Model, SerializerMixin):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    profile_picture_url = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(80), nullable=False)
    registration_date = db.Column(db.DateTime, nullable=False)
    is_confirmed = db.Column(db.Boolean, default=False)
    
    #relationship
    courses = db.relationship('Course', back_populates='instructor')
    enrollments = db.relationship('Enrollment', back_populates='user')
    discussions = db.relationship('Discussion', back_populates='user')
    comments = db.relationship('Comment', back_populates=None)  # One-directional relationship
    lesson_reviews = db.relationship('LessonReview', back_populates='user')
    lesson_progress = db.relationship('LessonProgress', back_populates='user')
    badges = db.relationship('UserBadge', back_populates='user')

    #serialization-rules
    serialize_rules = ('-courses.instructor',
                       '-enrollments.user',
                       '-discussions.user',
                       '-lesson_reviews.user',
                       '-comments.user',
                       '-lesson_progress.user')  # Exclude user reference in comments
    def get_course_progress(self, course_id):
        """Returns detailed progress stats for a course"""
        enrollment = Enrollment.query.filter_by(
            user_id=self.user_id,
            course_id=course_id
        ).first()
        
        if not enrollment:
            return None
            
        lessons = Lesson.query.filter_by(course_id=course_id).all()
        progress_data = []
        
        for lesson in lessons:
            progress = LessonProgress.query.filter_by(
                user_id=self.user_id,
                lesson_id=lesson.lesson_id
            ).first()
            
            progress_data.append({
                'lesson_id': lesson.lesson_id,
                'progress': progress.watched_duration / lesson.duration if (progress and lesson.duration) else 0,
                'completed': progress.is_completed if progress else False
            })
            
        return {
            'enrollment': enrollment,
            'lessons': progress_data
        }


class Course(db.Model, SerializerMixin):
    __tablename__ = 'courses'

    course_id = db.Column(db.Integer, primary_key=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False)
    last_update = db.Column(db.DateTime, nullable=False)
    course_image_url = db.Column(db.String(255), nullable=True)
    is_published = db.Column(db.Boolean, nullable=False)
    total_duration = db.Column(db.Integer, default=0)  

    #relationship
    instructor = db.relationship('User', back_populates='courses')
    lessons = db.relationship('Lesson', back_populates='course')
    enrollments = db.relationship('Enrollment', back_populates='course')
    discussions = db.relationship('Discussion', back_populates='course')

    #serialization-rules
    serialize_rules = ('-instructor.courses',
                       '-lessons.course',
                       '-enrollments.course',
                       '-discussions.course',)


class Lesson(db.Model, SerializerMixin):
    __tablename__ = 'lessons'

    lesson_id  = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.course_id'), nullable=False)
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    video_url = db.Column(db.String(255), nullable=False)
    duration = db.Column(db.Integer, nullable=True)
    #relationship
    course = db.relationship('Course', back_populates='lessons')
    lesson_reviews = db.relationship('LessonReview', back_populates='lesson')
    lesson_progress = db.relationship('LessonProgress', back_populates='lesson')

    #serialization-rules
    serialize_rules = ('-course.lessons','-lesson_reviews.lesson','-lesson_progress.lesson',)


class Enrollment(db.Model, SerializerMixin):
    __tablename__ = 'enrollments'   

    enrollment_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.course_id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.Column(db.Integer, default=0)  # Tracks progress as a percentage
    completed_date = db.Column(db.DateTime, nullable=True)  # Tracks when course was fully completed
    is_completed = db.Column(db.Boolean, default=False)
    show_celebration = db.Column(db.Boolean, default=False)  # Tracks if the user has seen the celebration
    #relationship
    user = db.relationship('User', back_populates='enrollments')
    course = db.relationship('Course', back_populates='enrollments')

    #serialization-rules
    serialize_rules = ('-user.enrollments','-course.enrollments',)

    def update_enrollment_progress(self):
        course_id = self.course_id
        user_id = self.user_id

        total_lessons = Lesson.query.filter_by(course_id=course_id).count()

        completed_lessons = LessonProgress.query.filter_by(
            user_id=user_id,
            is_completed=True
        ).join(Lesson).filter(Lesson.course_id == course_id).count()

        if total_lessons > 0:
            progress_percentage = (completed_lessons / total_lessons) * 100
        else:
            progress_percentage = 0

        enrollment = Enrollment.query.filter_by(
            user_id=user_id,
            course_id=course_id
        ).first()

        if enrollment:
            enrollment.progress = progress_percentage
            # Mark the course as completed if all lessons are completed
            enrollment.is_completed = (completed_lessons == total_lessons and total_lessons > 0)
            if enrollment.is_completed:
                enrollment.completed_date = datetime.utcnow()
            db.session.commit()




class Discussion(db.Model, SerializerMixin):
    __tablename__ = 'discussions'

    discussion_id = db.Column(db.Integer, primary_key=True)    
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.course_id'), nullable=False)
    title = db.Column(db.String(80), nullable=False)
    content = db.Column(db.String(255), nullable=False)
    discussion_date = db.Column(db.DateTime, nullable=False)

    #relationship
    user = db.relationship('User', back_populates='discussions')
    course = db.relationship('Course', back_populates='discussions')
    comments = db.relationship('Comment', back_populates=None)  # One-directional relationship

    # Custom property to access the user's username
    @property
    def user_username(self):
        return self.user.username if self.user else None

    #serialization-rules
    serialize_rules = ('-user', '-course', '-comments', 'user_username')  # Include user_username

class Comment(db.Model,SerializerMixin):
    __tablename__ = 'comments'

    comment_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussions.discussion_id'), nullable=False)
    content = db.Column(db.String(255), nullable=False)
    comment_date = db.Column(db.DateTime, nullable=False)

    # Custom property to access the user's username
    @property
    def user_username(self):
        user = User.query.get(self.user_id)
        return user.username if user else None

    # Custom property to access the discussion title
    @property
    def discussion_title(self):
        discussion = Discussion.query.get(self.discussion_id)
        return discussion.title if discussion else None

    #serialization-rules
    serialize_rules = ('discussion_title', 'user_username')  # Include user_username


class LessonReview(db.Model, SerializerMixin):
    __tablename__ = 'lesson_reviews'

    review_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.lesson_id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(255), nullable=False)
    review_date = db.Column(db.DateTime, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='lesson_reviews')
    lesson = db.relationship('Lesson', back_populates='lesson_reviews')

    # Serialization rules
    serialize_rules = (
        '-user',         
        '-lesson',       
        'user_username',  
        'user_first_name' 
    )

    # Custom property: Username
    @property
    def user_username(self):
        return self.user.username if self.user else None

    # Custom property: First Name
    @property
    def user_first_name(self):
        return self.user.first_name if self.user else None


class LessonProgress(db.Model, SerializerMixin):
    __tablename__ = 'lesson_progress'

    progress_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.lesson_id'), nullable=False)
    watched_duration = db.Column(db.Integer, nullable=False, default=0)  # In seconds
    is_completed = db.Column(db.Boolean, default=False)
    last_watched_date = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship('User', back_populates='lesson_progress')
    lesson = db.relationship('Lesson', back_populates='lesson_progress')

    # Custom properties for serialization
    @property
    def user_username(self):
        return self.user.username if self.user else None

    @property
    def lesson_title(self):
        return self.lesson.title if self.lesson else None

    # Serialization rules
    serialize_rules = ('-user', '-lesson', 'user_username', 'lesson_title')

    def check_completion(self, threshold=0.95):
        """Auto-mark complete if watched enough (call after updating watched_duration)"""
        if not self.is_completed and self.lesson.duration:
            if (self.watched_duration / self.lesson.duration) >= threshold:
                self.is_completed = True
                self.last_watched_date = datetime.utcnow()
        return self.is_completed

class Badge(db.Model, SerializerMixin):
    __tablename__ = 'badges'
    
    badge_id = db.Column(db.Integer, primary_key=True)
    emoji = db.Column(db.String(10), nullable=False)  # Stores the emoji character
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    criteria_type = db.Column(db.String(50), nullable=False)
    criteria_value = db.Column(db.String(255), nullable=True)
    tier = db.Column(db.String(20), nullable=True)
    xp_value = db.Column(db.Integer, default=0)
    is_hidden = db.Column(db.Boolean, default=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships remain the same
    user_badges = db.relationship('UserBadge', back_populates='badge')
    
    # Serialization rules
    serialize_rules = ('-user_badges.badge',)

class UserBadge(db.Model, SerializerMixin):
    __tablename__ = 'user_badges'
    
    user_badge_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.badge_id'), nullable=False)
    earned_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='badges')
    badge = db.relationship('Badge', back_populates='user_badges')
    
    # Serialization rules
    serialize_rules = ('-user', '-badge.user_badges')