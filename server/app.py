import os
from flask_restful import Api, Resource
from flask import Flask, request, make_response, jsonify
from flask_session import Session
from flask import session
from flask_cors import CORS
from flask_migrate import Migrate
from datetime import datetime
from database import db
from models import User, Course, Enrollment, Lesson, LessonReview, Discussion, Comment
from sqlalchemy.exc import IntegrityError
import boto3
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.compact = False
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = "PrinceZoku@2025//fjkjff48300/"
app.config['SESSION_FILE_DIR'] = './.flask_session' # Ensure this directory exists
app.config['SESSION_PERMANENT'] = False # Optional, set to True if you want sessions to persist

# Ensure the session directory exists
if not os.path.exists(app.config['SESSION_FILE_DIR']):
    os.makedirs(app.config['SESSION_FILE_DIR'])

CORS(app, supports_credentials=True)

migrate = Migrate(app, db)

db.init_app(app)
Session(app)
api = Api(app)

#amazon s3
s3 = boto3.client('s3')
BUCKET_NAME = 'skillbridge28'

#endpoints
class Logout(Resource):
    def get(self):
        session.pop('user_id', None)
        return make_response(jsonify({'message': 'Logged out successfully'}), 200)
    
class Login(Resource):
    def post(self):
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        user = User.query.filter_by(email=email).first()
        if not user:
            return make_response(jsonify({'error': 'User not found'}), 404)
        if user.password != password:
            return make_response(jsonify({'error': 'Incorrect password'}), 401) 
        session['user_id'] = user.user_id
        session.modified = True  # Ensure session is saved
        print("Login Session:", session)
        return make_response(jsonify({"message":"The login was successful"}), 200)


class UserPost(Resource):
    def post(self):
        data = request.get_json()
        try:
            user = User(
                username = data.get('username'),
                email = data.get('email'),
                password = data.get('password'),
                first_name = data.get('first_name'),
                last_name = data.get('last_name'),
                profile_picture_url = data.get('profile_picture_url'),
                bio = data.get('bio'),
                role = data.get('role'),
                registration_date = datetime.now()
            )
            db.session.add(user)
            db.session.commit()
            return make_response(user.to_dict(), 201)
        except IntegrityError:
            return make_response(jsonify({'error': 'Username or email already in use'}), 400)
        
    
class UserResource(Resource):
    def get(self, user_id):
        if user_id:
            user = User.query.filter_by(user_id=user_id).first()
            if not user:
                return make_response(jsonify({'error': 'User not found'}), 404)
            return make_response(jsonify(user.to_dict()), 200)
        

    

    def patch(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
                return make_response(jsonify({'error': 'User not found'}), 404)
        data = request.get_json()
        try:
            allowed_keys = ['username', 'email', 'password', 'first_name', 'last_name', 'profile_picture_url', 'bio', 'role']
            for key, value in data.items():
                if key in allowed_keys:
                    setattr(user, key, value)
            db.session.commit()
            return user.to_dict()
        except IntegrityError:
            return make_response(jsonify({'error': 'Username or email already in use'}), 400)
        

    def delete(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
                return make_response(jsonify({'error': 'User not found'}), 404)
        try:
            db.session.delete(user)
            db.session.commit()
            return make_response('', 204)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

class CourseById(Resource):
    def get(self, course_id):
        if course_id:
            course = Course.query.filter(Course.course_id == course_id).first()
            if not course:
                return make_response(jsonify({'error': 'Course not found'}), 404)
            return course.to_dict()
    def patch(self, course_id):
        data = request.get_json()
        try:
            course = Course.query.filter_by(course_id=course_id).first()
            if not course:
                return make_response(jsonify({'error': 'Course not found'}), 404)
            for key, value in data.items():
                setattr(course, key, value)
            db.session.commit()
            return make_response(jsonify(course.to_dict()), 200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)
    def delete(self, course_id):
        try:
            course = Course.query.filter_by(course_id=course_id).first()
            if not course:
                return make_response(jsonify({'error': 'Course not found'}), 404)
            db.session.delete(course)
            db.session.commit()
            return make_response('', 204)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)
        
class Courses(Resource):
    def get(self):
        """Fetch all courses from the database."""
        try:
            courses = Course.query.all()
            return jsonify([course.to_dict() for course in courses])
        except Exception as e:
            return make_response(jsonify({'error': 'Error fetching courses', 'details': str(e)}), 500)

    def post(self):
        """Handles course creation with file upload."""
        try:
            
            data = request.form
            file = request.files.get('file')  # Use `.get()` to avoid KeyError

            # Validate required fields
            required_fields = ['title', 'description', 'category']
            missing_fields = [field for field in required_fields if not data.get(field)]

            if missing_fields:
                return make_response(jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400)

            # Validate and process file upload
            file_url = None
            if file:
                if file.filename == '':
                    return make_response(jsonify({'error': 'No file selected'}), 400)

                # Secure the filename
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"

                # Upload to S3
                s3.upload_fileobj(file, BUCKET_NAME, unique_filename)
                file_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{unique_filename}"

            # Create new course
            course = Course(
                instructor_id=1,  # Use the logged-in user's ID
                title=data.get('title'),
                description=data.get('description'),
                category=data.get('category'),
                creation_date=datetime.utcnow(),
                last_update=datetime.utcnow(),
                course_image_url=file_url,
                is_published=True
            )

            # Save to database
            db.session.add(course)
            db.session.commit()

            return make_response(jsonify(course.to_dict()), 201)

        except Exception as e:
            db.session.rollback()  # Rollback transaction in case of failure
            return make_response(jsonify({'error': 'Course creation failed', 'details': str(e)}), 500)

        
class Enrollments(Resource):
    def get(self):
        enrollments = Enrollment.query.all()
        return make_response(jsonify([enrollment.to_dict() for enrollment in enrollments]),200)
    def post(self):
        data = request.get_json()
        enrollment = Enrollment(**data)
        db.session.add(enrollment)
        db.session.commit()
        return make_response(jsonify(enrollment.to_dict()), 201)
    def patch(self):
        data = request.get_json()
        enrollment = Enrollment.query.get(data['enrollment_id'])
        for key, value in data.items():
            setattr(enrollment, key, value)
        db.session.commit()
        return make_response(jsonify(enrollment.to_dict()), 200)
    def delete(self):
        data = request.get_json()
        enrollment = Enrollment.query.get(data['enrollment_id'])
        db.session.delete(enrollment)
        db.session.commit()
        return make_response('', 204)

class Lessons(Resource):
    def get(self):
        data = request.get_json()
        course_id = data.get('course_id')
        if not course_id:
            return make_response(jsonify({'error': 'Course ID is required'}), 400)
        try:
            if course_id:
                lessons = Lesson.query.filter_by(course_id=course_id).all()
                return make_response(jsonify([lesson.to_dict() for lesson in lessons]), 200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)
        
    def post(self):

        # Get form data
        data = request.form
        file = request.files.get('video')

        # Validate required fields
        required_fields = ['course_id', 'title', 'description']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return make_response(jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400)

        # Check if course exists
        course = Course.query.filter_by(course_id=data.get('course_id')).first()
        if not course:
            return make_response(jsonify({'error': 'Course not found'}), 404)

        # Handle file upload
        video_url = None
        if file:
            try:
                filename = secure_filename(file.filename)
                unique_filename = f"videos/{uuid.uuid4().hex}_{filename}"
                
                # Upload to S3
                s3.upload_fileobj(
                    file,
                    BUCKET_NAME,
                    unique_filename,
                    ExtraArgs={'ContentType': file.content_type}
                )
                
                # Construct file URL
                video_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{unique_filename}"

            except Exception as e:
                return make_response(jsonify({'error': 'File upload failed', 'details': str(e)}), 500)

        try:
            # Create lesson
            lesson = Lesson(
                course_id=data.get('course_id'),
                title=data.get('title'),
                description=data.get('description'),
                video_url=video_url,
            )

            db.session.add(lesson)
            db.session.commit()
            
            return make_response(jsonify({'message': 'Lesson created successfully', 'lesson': lesson.to_dict()}), 201)
        
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': 'Lesson creation failed', 'details': str(e)}), 500)
    def patch(self):
        data = request.get_json()
        lesson_id = data.get('lesson_id')
        try:
            lesson = Lesson.query.filter_by(lesson_id=lesson_id).first()
            if not lesson:
                return make_response(jsonify({'error': 'Lesson not found'}), 404)
            for key, value in data.items():
                setattr(lesson, key, value)
            db.session.commit()
            return make_response(jsonify(lesson.to_dict()), 200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)
        
    def delete(self):
        data = request.get_json()
        lesson_id = data.get('lesson_id')
        try:
            lesson = Lesson.query.filter_by(lesson_id=lesson_id).first()
            if not lesson:
                return make_response(jsonify({'error': 'Lesson not found'}), 404)
            db.session.delete(lesson)
            db.session.commit()
            return make_response('', 204)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

class LessonByID(Resource):
    def get(self, lesson_id):
        try:
            lesson = Lesson.query.filter_by(lesson_id  = lesson_id).first()
            if not lesson:
                    return make_response(jsonify({'error': 'Lesson not found'}), 404)
            return make_response(jsonify(lesson.to_dict()),200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

        

class FileUpload(Resource):
    def post(self):
        try:
            if 'file' not in request.files:
                return make_response(jsonify({'error': 'No file part'}), 400)
            file = request.files['file']
            if file.filename == '':
                return make_response(jsonify({'error': 'No selected file'}), 400)
            if file:
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                s3.upload_fileobj(file, BUCKET_NAME, unique_filename)
                file_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{unique_filename}"
                return make_response(jsonify({'message': 'File uploaded successfully', 'file_url': file_url}), 200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)
        

class Discussions(Resource):
    def get(self):
        """Fetch all discussions."""
        try:
            discussions = Discussion.query.all()
            return make_response(jsonify([discussion.to_dict() for discussion in discussions]), 200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

    def post(self):
        """Create a new discussion."""
        try:
            data = request.get_json()
            discussion = Discussion(
                user_id=data.get('user_id'),
                course_id=data.get('course_id'),
                title=data.get('title'),
                content=data.get('content'),
                discussion_date=datetime.utcnow()
            )
            db.session.add(discussion)
            db.session.commit()
            return make_response(jsonify(discussion.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)


class DiscussionById(Resource):
    def get(self, discussion_id):
        """Fetch a specific discussion by ID."""
        try:
            discussion = Discussion.query.filter_by(discussion_id=discussion_id).first()
            if not discussion:
                return make_response(jsonify({'error': 'Discussion not found'}), 404)
            return make_response(jsonify(discussion.to_dict()), 200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

    def patch(self, discussion_id):
        """Update a specific discussion."""
        try:
            data = request.get_json()
            discussion = Discussion.query.filter_by(discussion_id=discussion_id).first()
            if not discussion:
                return make_response(jsonify({'error': 'Discussion not found'}), 404)
            for key, value in data.items():
                setattr(discussion, key, value)
            db.session.commit()
            return make_response(jsonify(discussion.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)

    def delete(self, discussion_id):
        """Delete a specific discussion."""
        try:
            discussion = Discussion.query.filter_by(discussion_id=discussion_id).first()
            if not discussion:
                return make_response(jsonify({'error': 'Discussion not found'}), 404)
            db.session.delete(discussion)
            db.session.commit()
            return make_response('', 204)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)


class Comments(Resource):
    def get(self):
        """Fetch all comments."""
        try:
            comments = Comment.query.all()
            return make_response(jsonify([comment.to_dict() for comment in comments]), 200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

    def post(self):
        """Create a new comment."""
        try:
            data = request.get_json()
            comment = Comment(
                user_id=data.get('user_id'),
                discussion_id=data.get('discussion_id'),
                content=data.get('content'),
                comment_date=datetime.utcnow()
            )
            db.session.add(comment)
            db.session.commit()
            return make_response(jsonify(comment.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)


class CommentById(Resource):
    def get(self, comment_id):
        """Fetch a specific comment by ID."""
        try:
            comment = Comment.query.filter_by(comment_id=comment_id).first()
            if not comment:
                return make_response(jsonify({'error': 'Comment not found'}), 404)
            return make_response(jsonify(comment.to_dict()), 200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

    def patch(self, comment_id):
        """Update a specific comment."""
        try:
            data = request.get_json()
            comment = Comment.query.filter_by(comment_id=comment_id).first()
            if not comment:
                return make_response(jsonify({'error': 'Comment not found'}), 404)
            for key, value in data.items():
                setattr(comment, key, value)
            db.session.commit()
            return make_response(jsonify(comment.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)

    def delete(self, comment_id):
        """Delete a specific comment."""
        try:
            comment = Comment.query.filter_by(comment_id=comment_id).first()
            if not comment:
                return make_response(jsonify({'error': 'Comment not found'}), 404)
            db.session.delete(comment)
            db.session.commit()
            return make_response('', 204)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)

class Lessonreviews(Resource):
    def post(self):
        try:
            data = request.get_json()
            lesson_review = LessonReview(
                user_id=data.get('user_id'),
                lesson_id=data.get('lesson_id'),
                rating=data.get('rating'),
                comment=data.get('comment'),
                review_date=datetime.utcnow()
            )
            db.session.add(lesson_review)
            db.session.commit()
            return make_response(jsonify(lesson_review.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)

api.add_resource(Lessonreviews, '/lessonreviews')
api.add_resource(Logout, '/logout')
api.add_resource(Login, '/login')
api.add_resource(FileUpload, '/upload')
api.add_resource(UserResource ,'/users/<int:user_id>')
api.add_resource(CourseById, '/courses/<int:course_id>')
api.add_resource(Courses, '/courses')
api.add_resource(Enrollments, '/enrollments')
api.add_resource(Lessons, '/lessons')
api.add_resource(LessonByID, '/lessons/<int:lesson_id>')
api.add_resource(UserPost, '/users')
api.add_resource(Discussions, '/discussions')
api.add_resource(DiscussionById, '/discussions/<int:discussion_id>')
api.add_resource(Comments, '/comments')
api.add_resource(CommentById, '/comments/<int:comment_id>')

if __name__ == '__main__':
    app.run(debug=True)