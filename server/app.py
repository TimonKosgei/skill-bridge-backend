from flask_restful import Api, Resource
from flask import Flask, request, make_response, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from datetime import datetime
from database import db
from models import User, Course, Enrollment, Lesson
from sqlalchemy.exc import IntegrityError
import boto3
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.compact = False

CORS(app)

migrate = Migrate(app, db)

db.init_app(app)
api = Api(app)

#amazon s3
s3 = boto3.client('s3')
BUCKET_NAME = 'skillbridge28'

#endpoints
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
        courses = Course.query.all()
        return jsonify([course.to_dict() for course in courses])
    def post(self):
        data = request.get_json()
        try:
            course = Course(
                instructor_id = data.get('instructor_id'),
                title = data.get('title'),
                description = data.get('description'),
                category = data.get('category'),
                creation_date = datetime.now(),
                last_update = datetime.now(),
                course_image_url = data.get('course_image_url'),
                is_published = data.get('is_published')
            )
            db.session.add(course)
            db.session.commit()
            return make_response(jsonify(course.to_dict()), 201)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)
        
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
        data = request.get_json()
        try:
            lesson = Lesson(
                course_id = data.get('course_id'),
                title = data.get('title'),
                description = data.get('description'),
                video_url = data.get('video_url'),
                duration = data.get('duration'),
                lesson_order = data.get('lesson_order')
            )
            db.session.add(lesson)
            db.session.commit()
            return make_response(jsonify(lesson.to_dict()), 201)
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)
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

api.add_resource(FileUpload, '/upload')
api.add_resource(UserResource ,'/users/<int:user_id>')
api.add_resource(CourseById, '/courses/<int:course_id>')
api.add_resource(Courses, '/courses')
api.add_resource(Enrollments, '/enrollments')
api.add_resource(Lessons, '/lessons')
api.add_resource(UserPost, '/users')

if __name__ == '__main__':
    app.run(debug=True)