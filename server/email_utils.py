from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

mail = None  # Declare a global variable for the mail object

# Email configuration
def configure_mail(app):
    global mail  # Use the global variable
    app.config['SECRET_KEY'] = "PrinceZoku@2025//fjkjff48300/"
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'  
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'mail.skillbridge@gmail.com'  
    app.config['MAIL_PASSWORD'] = 'pgvcalpcjeujcugl' 
    app.config['MAIL_DEFAULT_SENDER'] = 'mail.skillbridge@gmail.com'

    mail = Mail(app)
    return mail

def send_email(subject, recipient, body):
    """Send an email using Flask-Mail."""
    try:
        msg = Message(subject, recipients=[recipient], body=body)
        mail.send(msg)  # Use the global mail object
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def generate_confirmation_token(email, secret_key):
    """Generate a secure token for email confirmation."""
    serializer = URLSafeTimedSerializer(secret_key)
    return serializer.dumps(email, salt='email-confirmation-salt')

def confirm_token(token, secret_key, expiration=3600):
    """Validate and decode the email confirmation token."""
    serializer = URLSafeTimedSerializer(secret_key)
    try:
        email = serializer.loads(token, salt='email-confirmation-salt', max_age=expiration)
        return email
    except Exception as e:
        print(f"Error confirming token: {e}")
        return None

def send_password_reset_email(email, secret_key, base_url):
    """Send a password reset email with a secure token."""
    token = generate_confirmation_token(email, secret_key)
    reset_url = f"{base_url}/reset-password/{token}"
    subject = "Password Reset Request"
    body = f"To reset your password, click the following link: {reset_url}\n\nIf you did not request this, please ignore this email."
    
    return send_email(subject, email, body)

def reset_password(token, new_password, secret_key, user_model):
    """Reset the user's password after validating the token."""
    email = confirm_token(token, secret_key)
    if not email:
        return False  # Invalid or expired token

    # Update the user's password in the database
    user = user_model.query.filter_by(email=email).first()
    if user:
        user.set_password(new_password)  # Assuming `set_password` hashes the password
        user_model.session.commit()
        return True
    return False