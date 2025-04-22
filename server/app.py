import os
import jwt  # Import PyJWT
import bcrypt  # Add this import
from flask_restful import Api, Resource
from flask import Flask, request, make_response, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from datetime import datetime, timedelta
from database import db
from models import User, Course, Enrollment, Lesson, LessonReview, Discussion, Comment, LessonProgress, UserBadge, Badge
from sqlalchemy.exc import IntegrityError
import boto3
from werkzeug.utils import secure_filename
import uuid
from moviepy.video.io.VideoFileClip import VideoFileClip  # Import for video duration
from badge_utils import check_and_award_badges

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.compact = False
app.secret_key = "PrinceZoku@2025//fjkjff48300/"  # Used for JWT signing

CORS(app, supports_credentials=True)

migrate = Migrate(app, db)

db.init_app(app)
api = Api(app)

# Amazon S3
s3 = boto3.client('s3', verify = False)
BUCKET_NAME = 'skillbridge28'

# JWT Helper Functions
def generate_jwt(user_id, username):
    """Generate a JWT token for the given user ID."""
    payload = {
        'user_id': user_id,
         'username':username,
        'exp': datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
    }
    token = jwt.encode(payload, app.secret_key, algorithm='HS256')
    return token

def decode_jwt(token):
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token


class Signup(Resource):
    def post(self):
        data = request.get_json()
        
        # Check if request data is valid JSON
        if not data:
            return make_response(jsonify({'error': 'No data provided'}), 400)
        
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if field not in data or not data.get(field):
                return make_response(jsonify({'error': f'{field} is required'}), 400)
        
        try:
            # Hash the password
            password = data.get('password')
            if not isinstance(password, str) or len(password) < 8:
                return make_response(jsonify({'error': 'Password must be at least 8 characters'}), 400)
            
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            user = User(
                username=data.get('username'),
                email=data.get('email'),
                password=hashed_password,
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                profile_picture_url=data.get('profile_picture_url', ''),  # Default empty string if not provided
                bio=data.get('bio', ''),
                role=data.get('role'),  
                registration_date=datetime.now()
            )
            
            db.session.add(user)
            db.session.commit()
            return make_response(jsonify(user.to_dict()), 201)
            
        except IntegrityError as e:
            db.session.rollback()
            if 'username' in str(e):
                return make_response(jsonify({'error': 'Username already in use'}), 400)
            elif 'email' in str(e):
                return make_response(jsonify({'error': 'Email already in use'}), 400)
            else:
                return make_response(jsonify({'error': 'Database integrity error'}), 400)
                
        except BadRequest:
            return make_response(jsonify({'error': 'Invalid JSON data'}), 400)
            
        except Exception as e:
            db.session.rollback()
            # Avoid exposing internal errors in production
            return make_response(jsonify({'error': 'Failed to create user'}), 500)

class Login(Resource):
    def post(self):
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        user = User.query.filter_by(email=email).first()
        if not user:
            return make_response(jsonify({'error': 'Invalid email or password'}), 401)
        if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            return make_response(jsonify({'error': 'Invalid email or password'}), 401)
        
        # Generate JWT token
        token = generate_jwt(user.user_id,user.username)
        return make_response(jsonify({"message": "Login successful", "token": token}), 200)

class UserPost(Resource):
    def post(self):
        data = request.get_json()
        try:
            # Hash the password
            hashed_password = bcrypt.hashpw(data.get('password').encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            user = User(
                username=data.get('username'),
                email=data.get('email'),
                password=hashed_password,  # Save the hashed password
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                profile_picture_url=data.get('profile_picture_url'),
                bio=data.get('bio'),
                role=data.get('role'),
                registration_date=datetime.now()
            )
            db.session.add(user)
            db.session.commit()
            return make_response(user.to_dict(), 201)
        except IntegrityError:
            return make_response(jsonify({'error': 'Username or email already in use'}), 400)
    def get(self):
        user_id = 1
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return make_response(jsonify({'error': 'User not found'}), 404)
        return make_response(jsonify(user.to_dict()), 200)
    

    
class UserResource(Resource):
    def get(self, user_id):
        
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return make_response(jsonify({'error': 'User not found'}), 404)
        return make_response(jsonify(user.to_dict()), 200)

    def patch(self, user_id):
        token = request.headers.get('Authorization')
        if not token:
            return make_response(jsonify({'error': 'Authorization token required'}), 401)
        
        decoded = decode_jwt(token)
        if not decoded:
            return make_response(jsonify({'error': 'Invalid or expired token'}), 401)
        
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
        token = request.headers.get('Authorization')
        if not token:
            return make_response(jsonify({'error': 'Authorization token required'}), 401)
        
        decoded = decode_jwt(token)
        if not decoded:
            return make_response(jsonify({'error': 'Invalid or expired token'}), 401)
        
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
            file = request.files.get('file') 
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
        return make_response(jsonify([enrollment.to_dict() for enrollment in enrollments]), 200)

    def post(self):
        data = request.get_json()
        user_id = data.get("user_id")
        course_id = data.get("course_id")

        # 1. Validate inputs
        if not user_id or not course_id:
            return make_response(jsonify({"error": "user_id and course_id are required"}), 400)

        # 2. Check if already enrolled
        existing_enrollment = Enrollment.query.filter_by(user_id=user_id, course_id=course_id).first()
        if existing_enrollment:
            return make_response(jsonify({"error": "User is already enrolled in this course"}), 409)

        # 3. Create the enrollment
        enrollment = Enrollment(
            user_id=user_id,
            course_id=course_id,
            enrollment_date=datetime.utcnow(),
            progress=0,
            is_completed=False
        )
        db.session.add(enrollment)
        db.session.flush()  # This ensures enrollment gets an ID if needed before committing

        # 4. Initialize lesson progress
        lessons = Lesson.query.filter_by(course_id=course_id).all()
        for lesson in lessons:
            lesson_progress = LessonProgress(
                user_id=user_id,
                lesson_id=lesson.lesson_id,
                watched_duration=0,
                is_completed=False
            )
            db.session.add(lesson_progress)

        # 5. Commit everything
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
    
class EnrollmentByCourseId(Resource):
    def get(self, course_id):
        enrollments = Enrollment.query.filter_by(course_id=course_id).all()
        if not enrollments:
            return make_response(jsonify({'error': 'No enrollments found for this course'}), 404)
        return make_response(jsonify([enrollment.to_dict() for enrollment in enrollments]), 200)

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
        file = request.files.get('file')

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
        video_duration = None
        if not file:
            return make_response(jsonify({'error': 'No video file provided'}), 400)
        if file:
            try:    
                # Create temp directory if it doesn't exist
                temp_dir = '/tmp/videos'
                os.makedirs(temp_dir, exist_ok=True)
                filename = secure_filename(file.filename)
                unique_filename = f"videos/{uuid.uuid4().hex}_{filename}"
                
                # Save the file temporarily to calculate duration
                temp_path = f"/tmp/{unique_filename}"
                file.save(temp_path)

                # Calculate video duration
                with VideoFileClip(temp_path) as video:
                    video_duration = video.duration  # Duration in seconds

                # Upload to S3
                s3.upload_file(
                    temp_path,
                    BUCKET_NAME,
                    unique_filename,
                    ExtraArgs={'ContentType': file.content_type}
                )
                
                # Construct file URL
                video_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{unique_filename}"

                # Remove the temporary file
                os.remove(temp_path)

            except Exception as e:
                return make_response(jsonify({'error': 'File upload failed', 'details': str(e)}), 500)

        try:
            # Create lesson
            lesson = Lesson(
                course_id=data.get('course_id'),
                title=data.get('title'),
                description=data.get('description'),
                video_url=video_url,
                duration=video_duration,  # Save the duration
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
        course_id = request.args.get("course_id")
        try:
            discussions = Discussion.query.filter_by(course_id=course_id).all()
            return make_response(jsonify([discussion.to_dict() for discussion in discussions]), 200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

    def post(self):
        """Create a new discussion."""
        try:
            data = request.get_json()
            user = User.query.filter_by(user_id=data.get('user_id')).first()
            discussion = Discussion(
                user_id=data.get('user_id'),
                course_id=data.get('course_id'),
                title=data.get('title'),
                content=data.get('content'),
                discussion_date=datetime.utcnow()
            )
            db.session.add(discussion)
            db.session.commit()
            # Check and award badges if criteria met
            check_and_award_badges(user)
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
            user = User.query.filter_by(user_id=data.get('user_id')).first()
            comment = Comment(
                user_id=data.get('user_id'),
                discussion_id=data.get('discussion_id'),
                content=data.get('content'),
                comment_date=datetime.utcnow()
            )
            db.session.add(comment)
            db.session.commit()
            #check and award badges if criteria met
            check_and_award_badges(user)
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
            user = User.query.filter_by(user_id=data.get('user_id')).first()
            comment = Comment.query.filter_by(comment_id=comment_id).first()
            if not comment:
                return make_response(jsonify({'error': 'Comment not found'}), 404)
            for key, value in data.items():
                setattr(comment, key, value)
            db.session.commit()
            # Check and award badges if criteria met
            check_and_award_badges(user)
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


# 1. Update or create LessonProgress
class LessonProgressResource(Resource):
    def post(self):
        data = request.get_json()
        user_id = data.get('user_id')
        lesson_id = data.get('lesson_id')
        watched_duration = data.get('watched_duration')

        lesson = Lesson.query.get(lesson_id)
        if not lesson:
            return {"message": "Lesson not found"}, 404

        progress = LessonProgress.query.filter_by(user_id=user_id, lesson_id=lesson_id).first()
        if not progress:
            progress = LessonProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                watched_duration=watched_duration,
                last_watched_date=datetime.utcnow()
            )
            db.session.add(progress)
        else:
            progress.watched_duration = watched_duration
            progress.last_watched_date = datetime.utcnow()

        # Check and mark as completed if enough is watched
        progress.check_completion()

        # Update enrollment progress if exists
        enrollment = Enrollment.query.filter_by(user_id=user_id, course_id=lesson.course_id).first()
        if enrollment:
            enrollment.update_completion_status()

        db.session.commit()
        return progress.to_dict(), 200
    def patch(self):
        data = request.get_json()
        user_id = data.get('user_id')
        lesson_id = data.get('lesson_id')
        watched_duration = data.get('watched_duration')

        user = User.query.get(user_id)
        progress = LessonProgress.query.filter_by(user_id=user_id, lesson_id=lesson_id).first()
        if not progress:
            return {"message": "Progress not found"}, 404

        progress.watched_duration = watched_duration
        progress.last_watched_date = datetime.utcnow()

        # Check and mark as completed if enough is watched
        progress.check_completion()

        #award badge
        check_and_award_badges(user)


        db.session.commit()
        # Update enrollment progress if exists
        enrollment = Enrollment.query.filter_by(user_id=user_id, course_id=progress.lesson.course_id).first()   
        
        enrollment.update_enrollment_progress()       
        
        return progress.to_dict(), 200


# 2. Get all lesson progress for a specific user
class UserProgressListResource(Resource):
    def get(self, user_id):
        progress = LessonProgress.query.filter_by(user_id=user_id).all()
        return [p.to_dict() for p in progress], 200


class Badges(Resource):
    def get(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return make_response(jsonify({'error': 'User not found'}), 404)
        badges = UserBadge.query.filter_by(user_id=user_id).all()
        return make_response(jsonify([badge.to_dict() for badge in badges]), 200)

class Leaderboard(Resource):
    def get(self):
        """Fetch users sorted by total XP."""
        try:
            # Query all users
            users = User.query.all()
            leaderboard = []

            for user in users:
                # Calculate total XP as the sum of XP from all badges the user has
                total_xp = sum(user_badge.badge.xp_value for user_badge in UserBadge.query.filter_by(user_id=user.user_id).all())

                leaderboard.append({
                    "user_id": user.user_id,
                    "name": f"{user.first_name} {user.last_name}",
                    "email": user.email,
                    "profile_picture": user.profile_picture_url,
                    "total_xp": total_xp
                })

            # Sort the leaderboard by total XP in descending order
            leaderboard.sort(key=lambda x: x['total_xp'], reverse=True)

            return make_response(jsonify(leaderboard), 200)
        except Exception as e:
            return make_response(jsonify({'error': 'Failed to fetch leaderboard', 'details': str(e)}), 500)

# Add the new resource to the API
api.add_resource(Leaderboard, '/leaderboard')

api.add_resource(Badges, '/users/<int:user_id>/badges')
api.add_resource(EnrollmentByCourseId, '/enrollments/<int:course_id>')
api.add_resource(LessonProgressResource, '/progress')
api.add_resource(UserProgressListResource, '/users/<int:user_id>/progress')
api.add_resource(Signup, '/signup')
api.add_resource(Lessonreviews, '/lessonreviews')
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