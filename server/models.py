from database import db
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

    #relationship
    courses = db.relationship('Course', back_populates='instructor')
    enrollments = db.relationship('Enrollment', back_populates='user')
    discussions = db.relationship('Discussion', back_populates='user')
    comments = db.relationship('Comment', back_populates=None)  # One-directional relationship
    lesson_reviews = db.relationship('LessonReview', back_populates='user')

    #serialization-rules
    serialize_rules = ('-courses.instructor',
                       '-enrollments.user',
                       '-discussions.user',
                       '-lesson_reviews.user',
                       '-comments.user')  # Exclude user reference in comments


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

    #relationship
    course = db.relationship('Course', back_populates='lessons')
    lesson_reviews = db.relationship('LessonReview', back_populates='lesson')
    #serialization-rules
    serialize_rules = ('-course.lessons','-lesson_reviews.lesson')

class Enrollment(db.Model, SerializerMixin):
    __tablename__ = 'enrollments'   

    enrollment_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.course_id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, nullable=False)
    progress = db.Column(db.Integer, nullable=False)

    #relationship
    user = db.relationship('User', back_populates='enrollments')
    course = db.relationship('Course', back_populates='enrollments')

    #serialization-rules
    serialize_rules = ('-user.enrollments','-course.enrollments',)



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
