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
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from email_utils import configure_mail, confirm_token,send_email, generate_confirmation_token
import json

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

# Configure S3 bucket policy to prevent direct downloads
s3.put_bucket_policy(
    Bucket=BUCKET_NAME,
    Policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowPublicRead",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": [
                    f"arn:aws:s3:::{BUCKET_NAME}/*"
                ]
            }
        ]
    })
)

# Configure CORS for the bucket
s3.put_bucket_cors(
    Bucket=BUCKET_NAME,
    CORSConfiguration={
        'CORSRules': [
            {
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET'],
                'AllowedOrigins': [
                    'http://localhost:3000',
                    'http://127.0.0.1:3000',
                    'http://localhost:5173',  # Vite default port
                    'http://127.0.0.1:5173'   # Vite default port
                ],
                'ExposeHeaders': ['ETag'],
                'MaxAgeSeconds': 3000
            }
        ]
    }
)

# Configure email
mail = configure_mail(app)

# JWT Helper Functions
def generate_jwt(user_id, username,role):
    """Generate a JWT token for the given user ID."""
    payload = {
        'user_id': user_id,
         'username':username,
         'role':role,
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

def token_required(f):
    """Decorator to protect routes that require JWT authentication."""
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return make_response(jsonify({'error': 'Token is missing'}), 401)
        
        # Decode token
        payload = decode_jwt(token)
        if not payload:
            return make_response(jsonify({'error': 'Invalid or expired token'}), 401)
        
        # Add user info to request context
        request.user = payload
        return f(*args, **kwargs)
    
    decorated.__name__ = f.__name__
    return decorated

def update_model(instance, data, allowed_fields):
    """Update the fields of a model instance with the provided data.
    """
    for key, value in data.items():
        if key in allowed_fields:
            setattr(instance, key, value)

class Signup(Resource):
    def post(self):
        data = request.get_json()
        
        # Validate input
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if field not in data or not data[field]:
                return {"error": f"{field} is required"}, 400
        
        # Hash the password
        hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user
        try:
            user = User(
                username=data.get('username'),
                email=data.get('email'),
                password=hashed_password,
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                role=data.get('role', 'Learner'), 
                registration_date=datetime.utcnow(),
                is_confirmed=False  # Add this field to track email confirmation
            )
            db.session.add(user)
            db.session.commit()
            
            # Generate confirmation token
            token = generate_confirmation_token(user.email, app.secret_key)
            confirm_url = f"http://localhost:3000/confirm/{token}"  # Replace with your frontend URL if needed
            
            # Send confirmation email
            subject = "Confirm Your Email"
            body = f"Please confirm your email by clicking the following link: {confirm_url}"
            if send_email(subject, user.email, body):
                return {"message": "User created successfully. Please check your email to confirm your account."}, 201
            else:
                return {"error": "Failed to send confirmation email"}, 500
        
        except IntegrityError:
            return make_response(jsonify({'error': 'Username or email already in use'}), 400)
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class Login(Resource):
    def post(self):
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        # Check if the user exists
        user = User.query.filter_by(email=email).first()
        if not user:
            return make_response(jsonify({'error': 'Invalid email or password'}), 401)

        # Check if the password is correct
        if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            return make_response(jsonify({'error': 'Invalid email or password'}), 401)

        # Check if the user's email is confirmed
        if not user.is_confirmed:
            # Generate a new confirmation token
            token = generate_confirmation_token(user.email, app.secret_key)
            confirm_url = f"http://localhost:3000/confirm/{token}"  # Replace with your frontend URL if needed

            # Send a new confirmation email
            subject = "Confirm Your Email"
            body = f"Please confirm your email by clicking the following link: {confirm_url}"
            if send_email( subject, user.email, body):
                return make_response(jsonify({
                    "error": "Email not confirmed. A new confirmation email has been sent to your email address."
                }), 403)
            else:
                return make_response(jsonify({
                    "error": "Email not confirmed, and we failed to send a confirmation email. Please try again later."
                }), 500)

        # Generate JWT token for confirmed users
        token = generate_jwt(user.user_id, user.username, user.role)
        return make_response(jsonify({"message": "Login successful", "token": token}), 200)

    
class UserResource(Resource):
    @token_required
    def get(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return make_response(jsonify({'error': 'User not found'}), 404)
        return make_response(jsonify(user.to_dict()), 200)

    @token_required
    def patch(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return make_response(jsonify({'error': 'User not found'}), 404)
        data = request.get_json()
        try:
            allowed_keys = ['username', 'email', 'password', 'first_name', 'last_name', 'profile_picture_url', 'bio', 'role']
            update_model(user, data, allowed_keys)  # Use the utility function
            db.session.commit()
            return user.to_dict()
        except IntegrityError:
            return make_response(jsonify({'error': 'Username or email already in use'}), 400)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)

    @token_required
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
    @token_required
    def get(self, course_id):
        if course_id:
            course = Course.query.filter(Course.course_id == course_id).first()
            if not course:
                return make_response(jsonify({'error': 'Course not found'}), 404)
            return course.to_dict()

    @token_required
    def patch(self, course_id):
        # Check if user is instructor or admin
        if request.user['role'] not in ['Instructor', 'Admin']:
            return make_response(jsonify({'error': 'Unauthorized - Only instructors and admins can update courses'}), 403)
            
        # Get form data and file
        data = request.form
        file = request.files.get('file')

        try:
            course = Course.query.filter_by(course_id=course_id).first()
            if not course:
                return make_response(jsonify({'error': 'Course not found'}), 404)

            # Check if user is the course instructor (unless admin)
            if request.user['role'] != 'Admin' and course.instructor_id != request.user['user_id']:
                return make_response(jsonify({'error': 'Unauthorized - You can only update your own courses'}), 403)

            # Handle file upload if provided
            if file:
                try:
                    # Delete old image from S3 if it exists
                    if course.course_image_url:
                        old_key = course.course_image_url.split(f'https://{BUCKET_NAME}.s3.amazonaws.com/')[-1]
                        s3.delete_object(Bucket=BUCKET_NAME, Key=old_key)

                    # Secure the filename
                    filename = secure_filename(file.filename)
                    unique_filename = f"course_images/{uuid.uuid4().hex}_{filename}"
                    
                    # Upload to S3
                    s3.upload_fileobj(
                        file,
                        BUCKET_NAME,
                        unique_filename,
                        ExtraArgs={'ContentType': file.content_type}
                    )
                    
                    # Update course with new image URL
                    course.course_image_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{unique_filename}"

                except Exception as e:
                    return make_response(jsonify({'error': 'Image update failed', 'details': str(e)}), 500)

            # Update other fields
            updatable_fields = ['title', 'description', 'category']
            for field in updatable_fields:
                if field in data:
                    setattr(course, field, data.get(field))
            if data.get('is_published'):
                if data.get('is_published') == 'true':
                    course.is_published = True
                else:
                    course.is_published = False

            # Update last_update timestamp
            course.last_update = datetime.utcnow()

            db.session.commit()
            return make_response(jsonify({
                'message': 'Course updated successfully',
                'course': course.to_dict()
            }), 200)

        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)

    @token_required
    def delete(self, course_id):
        # Check if user is instructor or admin
        if request.user['role'] not in ['Instructor', 'Admin']:
            return make_response(jsonify({'error': 'Unauthorized - Only instructors and admins can delete courses'}), 403)

        try:
            course = Course.query.filter_by(course_id=course_id).first()
            if not course:
                return make_response(jsonify({'error': 'Course not found'}), 404)

            # Check if user is the course instructor (unless admin)
            if request.user['role'] != 'Admin' and course.instructor_id != request.user['user_id']:
                return make_response(jsonify({'error': 'Unauthorized - You can only delete your own courses'}), 403)

            db.session.delete(course)
            db.session.commit()
            return make_response('', 204)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

class Courses(Resource):
    @token_required
    def get(self):
        """Fetch all courses from the database."""
        try:
            # If user is an instructor or admin, show all their courses
            if request.user['role'] in ['Instructor']:
                courses = Course.query.filter_by(instructor_id=request.user['user_id']).all()
            else:
                # For regular users, only show published courses
                courses = Course.query.filter_by(is_published=True).all()
            return jsonify([course.to_dict() for course in courses])
        except Exception as e:
            return make_response(jsonify({'error': 'Error fetching courses', 'details': str(e)}), 500)

    @token_required
    def post(self):
        """Handles course creation with file upload."""
        try:
            # Check if user is instructor or admin
            if request.user['role'] not in ['Instructor', 'Admin']:
                return make_response(jsonify({'error': 'Unauthorized - Only instructors and admins can create courses'}), 403)
            
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
                instructor_id=request.user['user_id'],
                title=data.get('title'),
                description=data.get('description'),
                category=data.get('category'),
                creation_date=datetime.utcnow(),
                last_update=datetime.utcnow(),
                course_image_url=file_url,
                is_published=data.get('is_published') == 'true'  # Convert string to boolean
            )

            # Save to database
            db.session.add(course)
            db.session.commit()

            return make_response(jsonify(course.to_dict()), 201)

        except Exception as e:
            db.session.rollback()  # Rollback transaction in case of failure
            return make_response(jsonify({'error': 'Course creation failed', 'details': str(e)}), 500)

class Enrollments(Resource):
    @token_required
    def get(self):
        enrollments = Enrollment.query.all()
        return make_response(jsonify([enrollment.to_dict() for enrollment in enrollments]), 200)

    @token_required
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

    @token_required
    def patch(self):
        data = request.get_json()
        show_contribution = data.get('show_celebration')
        enrollment = Enrollment.query.get(data['enrollment_id'])
        if not enrollment:
            return make_response(jsonify({'error': 'Enrollment not found'}), 404)
        try:
            if show_contribution:
                enrollment.show_celebration = True
            allowed_keys = ['progress', 'is_completed','show_celebration']
            update_model(enrollment, data, allowed_keys)  
            db.session.commit()
            return make_response(jsonify(enrollment.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)

    @token_required
    def delete(self):
        data = request.get_json()
        enrollment = Enrollment.query.get(data['enrollment_id'])
        db.session.delete(enrollment)
        db.session.commit()
        return make_response('', 204)
    
class EnrollmentByCourseId(Resource):
    @token_required
    def get(self, course_id):
        course = Course.query.filter_by(course_id=course_id).first()
        if not course:
            return make_response(jsonify({'error': 'Course not found'}), 404)
        
        enrollments = Enrollment.query.filter_by(course_id=course_id).all()
        if not enrollments:
            return make_response(jsonify([]), 200)
        
        return make_response(jsonify([enrollment.to_dict() for enrollment in enrollments]), 200)

class Lessons(Resource):
    @token_required
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
        
    @token_required
    def post(self):
        # Check if user is instructor or admin
        if request.user['role'] not in ['Instructor', 'Admin']:
            return make_response(jsonify({'error': 'Unauthorized - Only instructors and admins can create lessons'}), 403)

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

        # Check if user is the course instructor (unless admin)
        if request.user['role'] != 'Admin' and course.instructor_id != request.user['user_id']:
            return make_response(jsonify({'error': 'Unauthorized - You can only add lessons to your own courses'}), 403)

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
    

class LessonByID(Resource):
    @token_required
    def get(self, lesson_id):
        try:
            lesson = Lesson.query.filter_by(lesson_id  = lesson_id).first()
            if not lesson:
                    return make_response(jsonify({'error': 'Lesson not found'}), 404)
            return make_response(jsonify(lesson.to_dict()),200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

    @token_required
    def patch(self, lesson_id):
        # Check if user is instructor or admin
        if request.user['role'] not in ['Instructor', 'Admin']:
            return make_response(jsonify({'error': 'Unauthorized - Only instructors and admins can update lessons'}), 403)

        # Get form data and file
        data = request.form
        file = request.files.get('file')

        if not lesson_id:
            return make_response(jsonify({'error': 'Lesson ID is required'}), 400)

        try:
            lesson = Lesson.query.filter_by(lesson_id=lesson_id).first()
            if not lesson:
                return make_response(jsonify({'error': 'Lesson not found'}), 404)

            # Check if user is the course instructor (unless admin)
            course = Course.query.filter_by(course_id=lesson.course_id).first()
            if request.user['role'] != 'Admin' and course.instructor_id != request.user['user_id']:
                return make_response(jsonify({'error': 'Unauthorized - You can only update lessons in your own courses'}), 403)

            # Handle file upload if provided
            if file:
                try:
                    # Create temp directory
                    temp_dir = '/tmp/videos'
                    os.makedirs(temp_dir, exist_ok=True)
                    filename = secure_filename(file.filename)
                    unique_filename = f"videos/{uuid.uuid4().hex}_{filename}"
                    
                    # Save temp file for duration calculation
                    temp_path = f"/tmp/{unique_filename}"
                    file.save(temp_path)

                    # Calculate new duration
                    with VideoFileClip(temp_path) as video:
                        video_duration = video.duration

                    # Upload to S3
                    s3.upload_file(
                        temp_path,
                        BUCKET_NAME,
                        unique_filename,
                        ExtraArgs={'ContentType': file.content_type}
                    )
                    
                    # Delete old video from S3 if exists
                    if lesson.video_url:
                        old_key = lesson.video_url.split(f'https://{BUCKET_NAME}.s3.amazonaws.com/')[-1]
                        s3.delete_object(Bucket=BUCKET_NAME, Key=old_key)

                    # Update lesson with new video
                    lesson.video_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{unique_filename}"
                    lesson.duration = video_duration

                    # Cleanup temp file
                    os.remove(temp_path)

                except Exception as e:
                    return make_response(jsonify({'error': 'Video update failed', 'details': str(e)}), 500)

            # Update other fields
            updatable_fields = ['title', 'description']
            for field in updatable_fields:
                if field in data:
                    setattr(lesson, field, data.get(field))

            db.session.commit()
            return make_response(jsonify({
                'message': 'Lesson updated successfully',
                'lesson': lesson.to_dict()
            }), 200)

        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)
        
    @token_required
    def delete(self, lesson_id):
        # Check if user is instructor or admin
        if request.user['role'] not in ['Instructor', 'Admin']:
            return make_response(jsonify({'error': 'Unauthorized - Only instructors and admins can delete lessons'}), 403)

        data = request.get_json()
        
        if not lesson_id:
            return make_response(jsonify({'error': 'Lesson ID is required'}), 400)

        try:
            lesson = Lesson.query.filter_by(lesson_id=lesson_id).first()
            if not lesson:
                return make_response(jsonify({'error': 'Lesson not found'}), 404)

            # Check if user is the course instructor (unless admin)
            course = Course.query.filter_by(course_id=lesson.course_id).first()
            if request.user['role'] != 'Admin' and course.instructor_id != request.user['user_id']:
                return make_response(jsonify({'error': 'Unauthorized - You can only delete lessons from your own courses'}), 403)

            # Delete video from S3 if it exists
            if lesson.video_url:
                try:
                    key = lesson.video_url.split(f'https://{BUCKET_NAME}.s3.amazonaws.com/')[-1]
                    s3.delete_object(Bucket=BUCKET_NAME, Key=key)
                except Exception as s3_error:
                    # Log the error but continue with DB deletion
                    current_app.logger.error(f"Failed to delete S3 object: {str(s3_error)}")

            # Delete from database
            db.session.delete(lesson)
            db.session.commit()
            
            return make_response('', 204)

        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)
        
class Discussions(Resource):
    @token_required
    def get(self):
        """Fetch all discussions."""
        course_id = request.args.get("course_id")
        try:
            discussions = Discussion.query.filter_by(course_id=course_id).all()
            return make_response(jsonify([discussion.to_dict() for discussion in discussions]), 200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

    @token_required
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
    @token_required
    def get(self, discussion_id):
        """Fetch a specific discussion by ID."""
        try:
            discussion = Discussion.query.filter_by(discussion_id=discussion_id).first()
            if not discussion:
                return make_response(jsonify({'error': 'Discussion not found'}), 404)
            return make_response(jsonify(discussion.to_dict()), 200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

    @token_required
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

    @token_required
    def delete(self, discussion_id):
        """Delete a specific discussion."""
        try:
            data = request.get_json()
            user_id = data.get('user_id')
            discussion = Discussion.query.filter_by(discussion_id=discussion_id).first()
            if not discussion:
                return make_response(jsonify({'error': 'Discussion not found'}), 404)
            if user_id != discussion.user_id:
                return make_response(jsonify({'error': 'You are not authorized to delete this discussion'}), 403)
            db.session.delete(discussion)
            db.session.commit()
            return make_response('', 204)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)

class Comments(Resource):
    @token_required
    def get(self):
        """Fetch all comments."""
        try:
            comments = Comment.query.all()
            return make_response(jsonify([comment.to_dict() for comment in comments]), 200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

    @token_required
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

    @token_required
    def delete(self):
        """Delete a specific comment."""
        data = request.get_json()
        comment_id = data.get('comment_id')
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
    @token_required
    def get(self):
        """Fetch up to 3 lesson reviews with 5-star ratings."""
        try:
            lesson_reviews = LessonReview.query.filter_by(rating=5).limit(3).all()
            return make_response(jsonify([review.to_dict() for review in lesson_reviews]), 200)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

    @token_required
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

    @token_required
    def delete(self):
        try:
            data = request.get_json()
            review_id = data.get('review_id')
            lesson_review = LessonReview.query.filter_by(review_id=review_id).first()
            if not lesson_review:
                return make_response(jsonify({'error': 'Review not found'}), 404)
            db.session.delete(lesson_review)
            db.session.commit()
            return make_response('', 204)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)


# 1. Update or create LessonProgress
class LessonProgressResource(Resource):
    @token_required
    def get(Self):
        data = request.get_json()
        user_id = data.get('user_id')
        lessons = LessonProgress.query.filter_by(user_id=user_id).all()
        if not lessons:
            return make_response(jsonify({'error': 'No lessons found for this user'}), 404)
        return make_response(jsonify([lesson.to_dict() for lesson in lessons]), 200)

    @token_required
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


class Badges(Resource):
    @token_required
    def get(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return make_response(jsonify({'error': 'User not found'}), 404)
        badges = UserBadge.query.filter_by(user_id=user_id).all()
        return make_response(jsonify([badge.to_dict() for badge in badges]), 200)

class MarkBadgeNotificationShown(Resource):
    @token_required
    def patch(self, user_badge_id):
        user_badge = UserBadge.query.get(user_badge_id)
        if not user_badge:
            return make_response(jsonify({'error': 'Badge not found'}), 404)
        
        user_badge.notification_shown = True
        try:
            db.session.commit()
            return make_response(jsonify({'message': 'Badge notification marked as shown'}), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({'error': str(e)}), 500)

class Leaderboard(Resource):
    @token_required
    def get(self):
        """Fetch users sorted by total XP."""
        try:
            # Query all learners
            Learners = User.query.filter_by(role='Learner').all()
            leaderboard = []

            for learner in Learners:
                # Calculate total XP as the sum of XP from all badges the user has
                total_xp = sum(learner_badge.badge.xp_value for learner_badge in UserBadge.query.filter_by(user_id=learner.user_id).all())
            
                leaderboard.append({
                    "user_id": learner.user_id,
                    "name": f"{learner.first_name} {learner.last_name}",
                    "email": learner.email,
                    "profile_picture": learner.profile_picture_url,
                    "bio":learner.bio,
                    "username": learner.username,
                    "total_xp": total_xp
                })

            # Sort the leaderboard by total XP in descending order
            leaderboard.sort(key=lambda x: x['total_xp'], reverse=True)

            return make_response(jsonify(leaderboard), 200)
        except Exception as e:
            return make_response(jsonify({'error': 'Failed to fetch leaderboard', 'details': str(e)}), 500)

class ConfirmEmail(Resource):
    def get(self, token):
        email = confirm_token(token, app.secret_key)
        if not email:
            return {"error": "Invalid or expired token"}, 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return {"error": "User not found"}, 404
        
        user.is_confirmed = True
        db.session.commit()
        return {"message": "Email confirmed successfully"}, 200

class ForgotPassword(Resource):
    def post(self):
        data = request.get_json()
        email = data.get('email')

        if not email:
            return {"error": "Email is required"}, 400

        user = User.query.filter_by(email=email).first()
        if not user:
            return {"error": "User with this email does not exist"}, 404

        # Generate a reset token
        token = generate_confirmation_token(email, app.secret_key)

        # Construct the reset URL
        reset_url = f"http://localhost:3000/reset-password/{token}"  # Replace with your frontend URL

        # Send the reset email
        subject = "Password Reset Request"
        body = f"To reset your password, click the following link: {reset_url}\n\nIf you did not request this, please ignore this email."
        if send_email(subject, email, body):
            return {"message": "Password reset email sent successfully"}, 200
        else:
            return {"error": "Failed to send password reset email"}, 500

class ResetPassword(Resource):
    def post(self):
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('new_password')

        if not token or not new_password:
            return {"error": "Token and new password are required"}, 400

        # Validate the token
        email = confirm_token(token, app.secret_key)
        if not email:
            return {"error": "Invalid or expired token"}, 400

        # Find the user by email
        user = User.query.filter_by(email=email).first()
        if not user:
            return {"error": "User not found"}, 404

        # Hash the new password
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Update the user's password
        user.password = hashed_password
        db.session.commit()

        return {"message": "Password reset successfully"}, 200

class ProfilePhoto(Resource):
    @token_required
    def patch(self, user_id):
        try:
            # Get the user
            user = User.query.filter_by(user_id=user_id).first()
            if not user:
                return make_response(jsonify({'error': 'User not found'}), 404)

            # Get the file from request
            file = request.files.get('file')
            if not file:
                return make_response(jsonify({'error': 'No file provided'}), 400)

            # Delete old photo from S3 if it exists
            if user.profile_picture_url:
                try:
                    old_key = user.profile_picture_url.split(f'https://{BUCKET_NAME}.s3.amazonaws.com/')[-1]
                    s3.delete_object(Bucket=BUCKET_NAME, Key=old_key)
                except Exception as s3_error:
                    # Log the error but continue with new upload
                    current_app.logger.error(f"Failed to delete old S3 object: {str(s3_error)}")

            # Process and upload new photo
            try:
                # Secure the filename
                filename = secure_filename(file.filename)
                unique_filename = f"profile_photos/{uuid.uuid4().hex}_{filename}"
                
                # Upload to S3
                s3.upload_fileobj(
                    file,
                    BUCKET_NAME,
                    unique_filename,
                    ExtraArgs={'ContentType': file.content_type}
                )
                
                # Update user's profile picture URL
                user.profile_picture_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{unique_filename}"
                db.session.commit()

                return make_response(jsonify({
                    'message': 'Profile photo updated successfully',
                    'profile_picture_url': user.profile_picture_url
                }), 200)

            except Exception as e:
                db.session.rollback()
                return make_response(jsonify({'error': 'Failed to upload new profile photo', 'details': str(e)}), 500)

        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)

class PublicCourses(Resource):
    def get(self):
        """Fetch all published courses from the database for public access."""
        try:
            courses = Course.query.filter_by(is_published=True).all()
            return jsonify([course.to_dict() for course in courses])
        except Exception as e:
            return make_response(jsonify({'error': 'Error fetching courses', 'details': str(e)}), 500)

class PublicLessonReviews(Resource):
    def get(self):
        """Fetch public lesson reviews for the landing page."""
        try:
            # Add debug logging
            print("Attempting to fetch lesson reviews...")
            # Join with user table to ensure user relationship is loaded
            reviews = LessonReview.query.join(User).order_by(LessonReview.review_date.desc()).limit(6).all()
            print(f"Found {len(reviews)} reviews")
            serialized_reviews = [review.to_dict() for review in reviews]
            print("Successfully serialized reviews")
            return jsonify(serialized_reviews)
        except Exception as e:
            print(f"Error in PublicLessonReviews: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return make_response(jsonify({'error': 'Error fetching reviews', 'details': str(e)}), 500)

# Api resources
api.add_resource(ProfilePhoto, '/users/<int:user_id>/profile-photo')
api.add_resource(ResetPassword, '/reset-password')
api.add_resource(ForgotPassword, '/forgot-password')
api.add_resource(Leaderboard, '/leaderboard')
api.add_resource(Badges, '/users/<int:user_id>/badges')
api.add_resource(EnrollmentByCourseId, '/enrollments/<int:course_id>')
api.add_resource(LessonProgressResource, '/progress')
api.add_resource(Signup, '/signup')
api.add_resource(Lessonreviews, '/lessonreviews')
api.add_resource(Login, '/login')
api.add_resource(UserResource ,'/users/<int:user_id>')
api.add_resource(CourseById, '/courses/<int:course_id>')
api.add_resource(Courses, '/courses')
api.add_resource(Enrollments, '/enrollments')
api.add_resource(Lessons, '/lessons')
api.add_resource(LessonByID, '/lessons/<int:lesson_id>')
api.add_resource(Discussions, '/discussions')
api.add_resource(DiscussionById, '/discussions/<int:discussion_id>')
api.add_resource(Comments, '/comments')
api.add_resource(ConfirmEmail, '/confirm/<string:token>')
api.add_resource(PublicCourses, '/public/courses')
api.add_resource(PublicLessonReviews, '/public/lessonreviews')
api.add_resource(MarkBadgeNotificationShown, '/user-badges/<int:user_badge_id>/mark-shown')

if __name__ == '__main__':
    app.run(debug=True)