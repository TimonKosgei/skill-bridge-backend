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

    #serialization-rules
    serialize_rules = ('-courses.instructor','-enrollments.user',)


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
    #serialization-rules
    serialize_rules = ('-instructor.courses','-lessons.course',)

class Lesson(db.Model, SerializerMixin):
    __tablename__ = 'lessons'

    lesson_id  = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.course_id'), nullable=False)
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    video_url = db.Column(db.String(255), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    lesson_order = db.Column(db.Integer, nullable=False)

    #relationship
    course = db.relationship('Course', back_populates='lessons')
    #serialization-rules
    serialize_rules = ('-course.lessons',)

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
