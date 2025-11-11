# main.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, User, Internship, Application, Certificate, Notification
import jwt
import datetime
import re
from functools import wraps
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import cloudinary
import cloudinary.uploader
import cloudinary.api
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)

# Configure SQL Alchemy
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = secrets.token_hex(32)
# JWT Configuration
app.config["JWT_SECRET_KEY"] = secrets.token_hex(32)
app.config["SMTP_SERVER"] = "smtp.gmail.com"
app.config["SMTP_PORT"] = 587
app.config["SMTP_USERNAME"] = "skillbridge699@gmail.com"
app.config["SMTP_PASSWORD"] = "your-app-password"

# Cloudinary configuration
app.config['CLOUDINARY_CLOUD_NAME'] = 'dmpdjklk8'
app.config['CLOUDINARY_API_KEY'] = '818263697871535'
app.config['CLOUDINARY_API_SECRET'] = 'VqiSnFkkH4oznDjoS5RiwV4BKhE'

# Initialize extensions
db.init_app(app)

# Configure Cloudinary
cloudinary.config(
    cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
    api_key=app.config['CLOUDINARY_API_KEY'],
    api_secret=app.config['CLOUDINARY_API_SECRET']
)

# Password validation function
def validate_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one digit"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least one special character"
    return None

# JWT token required decorator - Enhanced version
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        current_user = None
        
        # Try to get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                if auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
                else:
                    token = auth_header
            except Exception as e:
                print(f"Error parsing auth header: {e}")
        
        # Try to authenticate with token
        if token:
            try:
                data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
                current_user = User.query.get(data['user_id'])
                
                if not current_user:
                    return jsonify({'message': 'Invalid token!'}), 401
                    
            except jwt.ExpiredSignatureError:
                return jsonify({'message': 'Token has expired!'}), 401
            except jwt.InvalidTokenError:
                # Token is invalid, fall back to session
                print("Invalid token, falling back to session authentication")
                pass
        
        # Fall back to session authentication
        if not current_user and 'user_id' in session:
            current_user = User.query.get(session['user_id'])
        
        # If no authentication method worked
        if not current_user:
            return jsonify({'message': 'Authentication required!'}), 401
        
        # Call the decorated function with the current user
        return f(current_user, *args, **kwargs)
    
    return decorated

# Helper function to calculate profile completion percentage
def calculate_profile_completion(user):
    """Calculate profile completion percentage based on filled fields"""
    total_fields = 0
    completed_fields = 0
    
    # Define fields and their weights
    field_weights = {
        'full_name': 15,
        'email': 10,
        'college': 10,
        'course': 10,
        'graduation_year': 10,
        'skills': 15,
        'description': 10,
        'resume_url': 15,
        'profile_picture': 5
    }
    
    # Check each field
    if user.full_name and user.full_name.strip():
        completed_fields += field_weights['full_name']
    total_fields += field_weights['full_name']
    
    if user.email and user.email.strip():
        completed_fields += field_weights['email']
    total_fields += field_weights['email']
    
    if user.college and user.college.strip():
        completed_fields += field_weights['college']
    total_fields += field_weights['college']
    
    if user.course and user.course.strip():
        completed_fields += field_weights['course']
    total_fields += field_weights['course']
    
    if user.graduation_year:
        completed_fields += field_weights['graduation_year']
    total_fields += field_weights['graduation_year']
    
    if user.skills and user.skills.strip():
        completed_fields += field_weights['skills']
    total_fields += field_weights['skills']
    
    if user.description and user.description.strip():
        completed_fields += field_weights['description']
    total_fields += field_weights['description']
    
    if user.resume_url:
        completed_fields += field_weights['resume_url']
    total_fields += field_weights['resume_url']
    
    if user.profile_picture:
        completed_fields += field_weights['profile_picture']
    total_fields += field_weights['profile_picture']
    
    # Calculate percentage (ensure it doesn't exceed 100%)
    completion_percentage = min(100, completed_fields)
    
    return completion_percentage

# Send email function
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['SMTP_USERNAME']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(app.config['SMTP_SERVER'], app.config['SMTP_PORT'])
        server.starttls()
        server.login(app.config['SMTP_USERNAME'], app.config['SMTP_PASSWORD'])
        text = msg.as_string()
        server.sendmail(app.config['SMTP_USERNAME'], to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# Routes
@app.route("/")
def home():
    return render_template("homepage.html")

@app.route("/auth")
def auth_home():
    return render_template("index.html")

# User Registration

@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        email = data.get("email")
        password = data.get("password")
        confirm_password = data.get("confirm_password")
        user_type = data.get("user_type")
        full_name = data.get("full_name")
        mobile = data.get("mobile")
        college = data.get("college")
        course = data.get("course")
        company_name = data.get("company_name")
        industry = data.get("industry")
        company_size = data.get("company_size")
        website = data.get("website")
        description = data.get("description")
        location = data.get("location")
        contact_person = data.get("contact_person")
        skills = data.get("skills")
        graduation_year = data.get("graduation_year")
        
        # Validation
        if not email or not password:
            return jsonify({"error": "Email and password are required!"}), 400
            
        if password != confirm_password:
            return jsonify({"error": "Passwords do not match!"}), 400
            
        # Validate password strength
        password_error = validate_password(password)
        if password_error:
            return jsonify({"error": password_error}), 400
            
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already registered!"}), 400
        
        # Create new user - Save all provided company data
        new_user = User(
            email=email, 
            user_type=user_type,
            full_name=full_name,
            mobile=mobile,
            college=college,
            course=course,
            company_name=company_name,
            industry=industry,
            company_size=company_size,
            website=website,
            description=description,
            location=location,
            contact_person=contact_person,
            skills=skills,
            graduation_year=graduation_year
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        # Generate JWT token
        token = jwt.encode({
            'user_id': new_user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, app.config['JWT_SECRET_KEY'], algorithm='HS256')
        
        # Set session for traditional auth
        session["user_id"] = new_user.id
        session["user_email"] = new_user.email
        session["user_type"] = new_user.user_type
        
        return jsonify({
            "success": True,
            "message": "Registration successful!",
            "token": token,
            "user_type": user_type,
            "redirect_url": "/student-dashboard" if user_type == "student" else "/company-dashboard"
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Registration failed. Please try again."}), 500

# User Login
@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        user_type = data.get("user_type", "student")
        
        if not email or not password:
            return jsonify({"error": "Email and password are required!"}), 400
        
        user = User.query.filter_by(email=email, user_type=user_type).first()
        
        if user and user.check_password(password):
            # Generate JWT token
            token = jwt.encode({
                'user_id': user.id,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
            }, app.config['JWT_SECRET_KEY'], algorithm='HS256')
            
            # Set session
            session["user_id"] = user.id
            session["user_email"] = user.email
            session["user_type"] = user.user_type
            
            # Return proper redirect URL based on user type
            redirect_url = "/student-dashboard" if user.user_type == "student" else "/company-dashboard"
            
            return jsonify({
                "success": True,
                "message": f"Welcome back, {user.full_name or user.email}!",
                "token": token,
                "user_type": user.user_type,
                "redirect_url": redirect_url
            }), 200
        else:
            return jsonify({"error": "Invalid email or password!"}), 401
            
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "Login failed. Please try again."}), 500

# Forgot Password
@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    try:
        data = request.get_json()
        email = data.get("email")
        
        if not email:
            return jsonify({"error": "Email is required!"}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            reset_token = user.generate_reset_token()
            db.session.commit()
            
            # Send reset email
            reset_url = f"http://localhost:5000/reset-password?token={reset_token}"
            email_body = f"""
            <h3>Password Reset Request</h3>
            <p>Click the link below to reset your password:</p>
            <a href="{reset_url}">Reset Password</a>
            <p>This link will expire in 1 hour.</p>
            """
            
            if send_email(email, "Password Reset Request", email_body):
                return jsonify({"message": "Password reset link sent to your email"}), 200
            else:
                return jsonify({"error": "Failed to send email. Please try again."}), 500
        else:
            return jsonify({"error": "Email not found!"}), 404
            
    except Exception as e:
        return jsonify({"error": "Failed to process request. Please try again."}), 500

# Reset Password
@app.route("/reset-password", methods=["POST"])
def reset_password():
    try:
        data = request.get_json()
        token = data.get("token")
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")
        
        if not token or not new_password:
            return jsonify({"error": "Token and new password are required!"}), 400
            
        if new_password != confirm_password:
            return jsonify({"error": "Passwords do not match!"}), 400
            
        # Validate password strength
        password_error = validate_password(new_password)
        if password_error:
            return jsonify({"error": password_error}), 400
        
        user = User.query.filter_by(reset_token=token).first()
        
        if user and user.reset_token_expiry and user.reset_token_expiry > datetime.datetime.utcnow():
            user.set_password(new_password)
            user.reset_token = None
            user.reset_token_expiry = None
            db.session.commit()
            
            return jsonify({"message": "Password reset successfully!"}), 200
        else:
            return jsonify({"error": "Invalid or expired reset token!"}), 400
            
    except Exception as e:
        return jsonify({"error": "Failed to reset password. Please try again."}), 500

# Dashboard routes
@app.route("/student-dashboard")
@token_required
def student_dashboard(current_user=None):
    if not current_user:
        # Try to get user from session
        if 'user_id' in session:
            current_user = User.query.get(session['user_id'])
        else:
            flash("Please login first!", "error")
            return redirect(url_for('auth_home'))
    
    if current_user.user_type != 'student':
        flash("Access denied!", "error")
        return redirect(url_for('auth_home'))
    
    return render_template("student_dashboard.html", user=current_user)

@app.route("/company-dashboard")
@token_required
def company_dashboard(current_user=None):
    if not current_user:
        # Try to get user from session
        if 'user_id' in session:
            current_user = User.query.get(session['user_id'])
        else:
            flash("Please login first!", "error")
            return redirect(url_for('auth_home'))
    
    if current_user.user_type != 'company':
        flash("Access denied!", "error")
        return redirect(url_for('auth_home'))
    
    return render_template("company_dashboard.html", user=current_user)

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

# Check authentication status
@app.route("/check-auth")
def check_auth():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return jsonify({
                "authenticated": True,
                "user_type": user.user_type,
                "email": user.email
            }), 200
    
    return jsonify({"authenticated": False}), 200

# Auth status check endpoint
@app.route("/api/auth/check")
@token_required
def check_auth_status(current_user):
    return jsonify({
        "authenticated": True,
        "user_type": current_user.user_type,
        "email": current_user.email
    }), 200

# Add sample internships data
@app.route("/api/create-sample-internships", methods=["POST"])
def create_sample_internships():
    """Create sample internships for testing"""
    try:
        # Check if sample internships already exist
        existing_internships = Internship.query.first()
        if existing_internships:
            return jsonify({"success": True, "message": "Sample internships already exist"})
        
        # Create sample companies if they don't exist
        sample_companies = [
            {
                "email": "techcorp@example.com",
                "company_name": "TechCorp Solutions",
                "user_type": "company"
            },
            {
                "email": "innovate@example.com", 
                "company_name": "Innovate Labs",
                "user_type": "company"
            },
            {
                "email": "designstudio@example.com",
                "company_name": "Design Studio",
                "user_type": "company"
            }
        ]
        
        company_users = []
        for company_data in sample_companies:
            user = User.query.filter_by(email=company_data["email"]).first()
            if not user:
                user = User(
                    email=company_data["email"],
                    company_name=company_data["company_name"],
                    user_type=company_data["user_type"]
                )
                user.set_password("password123")
                db.session.add(user)
                company_users.append(user)
        
        db.session.commit()
        
        # Sample internships data
        sample_internships = [
            {
                "title": "Backend Developer Intern",
                "company_id": company_users[0].id,
                "description": "Join our backend team to develop scalable APIs and microservices using Python and Node.js. You'll work on real-world projects and gain experience with cloud technologies.",
                "requirements": "Strong knowledge of Python, REST APIs, Database design. Experience with Flask/Django is a plus. Understanding of software development principles.",
                "skills_required": "Python,SQL,API Development,Backend,Flask,Django,PostgreSQL",
                "internship_type": "backend",
                "location": "Remote",
                "salary": "$2000/month",
                "duration": "6 months",
                "is_published": True
            },
            {
                "title": "Python Developer Intern", 
                "company_id": company_users[0].id,
                "description": "Work on data processing pipelines and automation scripts using Python. You'll help build tools that process millions of data points daily.",
                "requirements": "Proficiency in Python, data structures, algorithms. Knowledge of pandas/numpy is beneficial. Experience with data analysis.",
                "skills_required": "Python,Data Analysis,Automation,Scripting,Pandas,NumPy",
                "internship_type": "backend", 
                "location": "Hybrid",
                "salary": "$1800/month",
                "duration": "3 months",
                "is_published": True
            },
            {
                "title": "Frontend Developer Intern",
                "company_id": company_users[1].id,
                "description": "Build responsive user interfaces and interactive web applications using React.js. Collaborate with designers to implement pixel-perfect designs.",
                "requirements": "Experience with HTML, CSS, JavaScript. Familiarity with React.js and modern frontend tools. Understanding of responsive design.",
                "skills_required": "JavaScript,React,HTML,CSS,Frontend,Responsive Design",
                "internship_type": "frontend",
                "location": "On-site", 
                "salary": "$1900/month",
                "duration": "4 months",
                "is_published": True
            },
            {
                "title": "React.js Intern",
                "company_id": company_users[1].id,
                "description": "Develop single-page applications and reusable React components. Work with state management and modern React patterns.",
                "requirements": "Strong JavaScript fundamentals, experience with React hooks and state management. Knowledge of modern ES6+ features.",
                "skills_required": "React,JavaScript,SPA,Web Development,State Management",
                "internship_type": "frontend",
                "location": "Remote",
                "salary": "$1700/month", 
                "duration": "5 months",
                "is_published": True
            },
            {
                "title": "UI/UX Design Intern",
                "company_id": company_users[2].id,
                "description": "Create user-centered designs and prototypes for web and mobile applications. Conduct user research and usability testing.",
                "requirements": "Understanding of design principles, experience with Figma/Adobe XD. Portfolio required. Knowledge of user research methods.",
                "skills_required": "UI Design,UX Research,Figma,Wireframing,Prototyping,User Testing",
                "internship_type": "ui/ux",
                "location": "Remote",
                "salary": "$1600/month",
                "duration": "4 months",
                "is_published": True
            },
            {
                "title": "Product Design Intern",
                "company_id": company_users[2].id, 
                "description": "Collaborate with product team to design intuitive user experiences and interfaces. Create design systems and component libraries.",
                "requirements": "Knowledge of user research, wireframing, prototyping. Creative problem-solving skills. Experience with design systems.",
                "skills_required": "Product Design,User Research,Prototyping,Design Thinking,Design Systems",
                "internship_type": "ui/ux",
                "location": "Hybrid",
                "salary": "$1750/month",
                "duration": "6 months",
                "is_published": True
            }
        ]
        
        for internship_data in sample_internships:
            internship = Internship(**internship_data)
            db.session.add(internship)
        
        db.session.commit()
        return jsonify({"success": True, "message": "Sample internships created successfully!"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# Student Profile API - Enhanced Version
@app.route("/api/student/profile", methods=["GET", "PUT"])
@token_required
def student_profile(current_user):
    if request.method == "GET":
        try:
            # Get student profile with certificates
            certificates = Certificate.query.filter_by(student_id=current_user.id).all()
            certificates_data = [
                {
                    "id": cert.id,
                    "name": cert.name,
                    "url": cert.file_url,
                    "uploaded_at": cert.uploaded_at.isoformat()
                } for cert in certificates
            ]
            
            # Parse skills from comma-separated string to list
            skills_list = []
            if current_user.skills:
                skills_list = [skill.strip() for skill in current_user.skills.split(',') if skill.strip()]
            
            # Calculate completion percentage
            completion_percentage = calculate_profile_completion(current_user)
            
            profile_data = {
                "success": True,
                "profile": {
                    "id": current_user.id,
                    "email": current_user.email,
                    "full_name": current_user.full_name or "",
                    "mobile": current_user.mobile or "",
                    "college": current_user.college or "",
                    "course": current_user.course or "",
                    "graduation_year": current_user.graduation_year or "",
                    "skills": skills_list,
                    "bio": current_user.description or "",
                    "about_self": getattr(current_user, 'about_self', '') or "",
                    "resume_url": current_user.resume_url or "",
                    "portfolio_url": getattr(current_user, 'portfolio_url', '') or "",
                    "profile_picture": getattr(current_user, 'profile_picture', '') or "",
                    "social_links": {
                        "github": getattr(current_user, 'github', '') or "",
                        "linkedin": getattr(current_user, 'linkedin', '') or "",
                        "leetcode": getattr(current_user, 'leetcode', '') or "",
                        "hackerrank": getattr(current_user, 'hackerrank', '') or ""
                    },
                    "certificates": certificates_data,
                    "completion_percentage": completion_percentage
                }
            }
            return jsonify(profile_data), 200
            
        except Exception as e:
            print(f"Error getting profile: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    elif request.method == "PUT":
        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "No data provided"}), 400
            
            print(f"Updating profile with data: {data}")  # Debug log
            
            # Update basic profile fields
            update_fields = [
                'full_name', 'mobile', 'college', 'course', 'graduation_year', 
                'description', 'about_self', 'portfolio_url'
            ]
            
            for field in update_fields:
                if field in data:
                    if field == 'description':
                        current_user.description = data[field] or ""
                    elif field == 'about_self':
                        current_user.about_self = data[field] or ""
                    elif field == 'portfolio_url':
                        current_user.portfolio_url = data[field] or ""
                    else:
                        setattr(current_user, field, data[field] or "")
            
            # Handle skills - convert list to comma-separated string
            if 'skills' in data:
                if isinstance(data['skills'], list):
                    skills_string = ','.join([skill.strip() for skill in data['skills'] if skill.strip()])
                    current_user.skills = skills_string
                else:
                    current_user.skills = data['skills'] or ""
            
            # Update social links
            if 'social_links' in data:
                social_links = data['social_links'] or {}
                current_user.github = social_links.get('github', '') or ""
                current_user.linkedin = social_links.get('linkedin', '') or ""
                current_user.leetcode = social_links.get('leetcode', '') or ""
                current_user.hackerrank = social_links.get('hackerrank', '') or ""
            
            # Calculate profile completion percentage
            completion_percentage = calculate_profile_completion(current_user)
            
            db.session.commit()
            
            # Return updated profile with completion percentage
            return jsonify({
                "success": True, 
                "message": "Profile updated successfully",
                "completion_percentage": completion_percentage
            }), 200
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating profile: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

# File Upload APIs
@app.route("/api/student/upload-profile-picture", methods=["POST"])
@token_required
def upload_profile_picture(current_user):
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            file,
            folder=f"skillbridge/profile_pictures/{current_user.id}",
            public_id=f"profile_{current_user.id}_{uuid.uuid4().hex[:8]}",
            overwrite=True
        )
        
        # Save URL to database
        current_user.profile_picture = upload_result['secure_url']
        db.session.commit()
        
        # Calculate new completion percentage
        completion_percentage = calculate_profile_completion(current_user)
        
        return jsonify({
            "success": True, 
            "message": "Profile picture uploaded successfully",
            "image_url": upload_result['secure_url'],
            "completion_percentage": completion_percentage
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/student/upload-resume", methods=["POST"])
@token_required
def upload_resume(current_user):
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
                # Check file type - allow IMAGE formats ONLY
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        file_extension = os.path.splitext(file.filename.lower())[1]
        if file_extension not in allowed_extensions:
            return jsonify({"success": False, "error": "Only image files (JPG, PNG, GIF, WEBP) are allowed."}), 400
        
        # Check file size (5MB limit - matching frontend)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        if file_size > 5 * 1024 * 1024:  # 5MB in bytes
            return jsonify({"success": False, "error": "File size must be less than 5MB."}), 400
        
        # Upload to Cloudinary as an image
        upload_result = cloudinary.uploader.upload(
            file,
            folder=f"skillbridge/resumes/{current_user.id}",
            public_id=f"resume_{current_user.id}_{uuid.uuid4().hex[:8]}",
            resource_type="image"
        )
        
        # Save URL to database
        current_user.resume_url = upload_result['secure_url']
        db.session.commit()
        
        # Calculate new completion percentage
        completion_percentage = calculate_profile_completion(current_user)
        
        return jsonify({
            "success": True, 
            "message": "Resume uploaded successfully",
            "resume_url": upload_result['secure_url'],
            "completion_percentage": completion_percentage
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/student/upload-certificate", methods=["POST"])
@token_required
def upload_certificate(current_user):
    try:
        if 'file' not in request.files or 'name' not in request.form:
            return jsonify({"success": False, "error": "File and name are required"}), 400
        
        file = request.files['file']
        name = request.form['name']
        
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            file,
            folder=f"skillbridge/certificates/{current_user.id}",
            public_id=f"cert_{current_user.id}_{uuid.uuid4().hex[:8]}",
            resource_type="auto"
        )
        
        # Create certificate record
        new_certificate = Certificate(
            student_id=current_user.id,
            name=name,
            file_url=upload_result['secure_url']
        )
        db.session.add(new_certificate)
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Certificate uploaded successfully",
            "certificate": {
                "id": new_certificate.id,
                "name": new_certificate.name,
                "url": new_certificate.file_url,
                "uploaded_at": new_certificate.uploaded_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/student/certificates/<int:certificate_id>", methods=["DELETE"])
@token_required
def delete_certificate(current_user, certificate_id):
    try:
        certificate = Certificate.query.filter_by(id=certificate_id, student_id=current_user.id).first()
        
        if not certificate:
            return jsonify({"success": False, "error": "Certificate not found"}), 404
        
        db.session.delete(certificate)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Certificate deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# Internships API - Only show published internships to students
@app.route("/api/internships", methods=["GET"])
@token_required
def get_internships(current_user):
    try:
        # Get query parameters
        search = request.args.get('search', '')
        skills = request.args.get('skills', '')
        internship_type = request.args.get('type', '')
        location = request.args.get('location', '')
        limit = request.args.get('limit', 10, type=int)
        
        # Base query - only show published internships to students
        query = Internship.query.filter_by(is_active=True, is_published=True)
        
        # Apply filters
        if search:
            query = query.filter(
                db.or_(
                    Internship.title.ilike(f'%{search}%'),
                    Internship.description.ilike(f'%{search}%'),
                    Internship.requirements.ilike(f'%{search}%')
                )
            )
        
        if skills:
            skill_list = [skill.strip() for skill in skills.split(',')]
            for skill in skill_list:
                query = query.filter(Internship.skills_required.ilike(f'%{skill}%'))
        
        if internship_type:
            query = query.filter(Internship.internship_type == internship_type)
        
        if location:
            query = query.filter(Internship.location.ilike(f'%{location}%'))
        
        internships = query.limit(limit).all()
        
        internships_data = []
        for internship in internships:
            company = User.query.get(internship.company_id)
            skills_list = internship.skills_required.split(',') if internship.skills_required else []
            
            # Check if student has already applied
            has_applied = False
            if current_user.user_type == 'student':
                existing_application = Application.query.filter_by(
                    student_id=current_user.id,
                    internship_id=internship.id
                ).first()
                has_applied = existing_application is not None
            
            internships_data.append({
                "id": internship.id,
                "title": internship.title,
                "company_name": company.company_name if company else "Unknown Company",
                "description": internship.description,
                "requirements": internship.requirements,
                "skills_required": skills_list,
                "type": internship.internship_type,
                "location": internship.location,
                "salary": internship.salary,
                "duration": internship.duration,
                "created_at": internship.created_at.isoformat(),
                "has_applied": has_applied
            })
        
        return jsonify({
            "success": True,
            "internships": internships_data
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Applications API
@app.route("/api/applications", methods=["GET", "POST", "DELETE"])
@token_required
def applications(current_user):
    if request.method == "GET":
        try:
            applications = Application.query.filter_by(student_id=current_user.id).all()
            
            applications_data = []
            for app in applications:
                internship = Internship.query.get(app.internship_id)
                company = User.query.get(internship.company_id) if internship else None
                
                applications_data.append({
                    "id": app.id,
                    "internship_id": app.internship_id,
                    "internship_title": internship.title if internship else "Unknown Position",
                    "company_name": company.company_name if company else "Unknown Company",
                    "status": app.status,
                    "applied_date": app.applied_date.isoformat(),
                    "updated_at": app.updated_at.isoformat(),
                    "cover_letter": app.cover_letter
                })
            
            return jsonify({
                "success": True,
                "applications": applications_data
            }), 200
            
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    elif request.method == "POST":
        try:
            data = request.get_json()
            internship_id = data.get('internship_id')
            cover_letter = data.get('cover_letter', '')
            
            if not internship_id:
                return jsonify({"success": False, "error": "Internship ID is required"}), 400
            
            # Check if internship exists and is published
            internship = Internship.query.filter_by(id=internship_id, is_published=True).first()
            if not internship:
                return jsonify({"success": False, "error": "Internship not found or not available"}), 404
            
            # Check if already applied
            existing_application = Application.query.filter_by(
                student_id=current_user.id, 
                internship_id=internship_id
            ).first()
            
            if existing_application:
                return jsonify({"success": False, "error": "You have already applied to this internship"}), 400
            
            # Create new application
            new_application = Application(
                student_id=current_user.id,
                internship_id=internship_id,
                cover_letter=cover_letter,
                status='applied'
            )
            
            db.session.add(new_application)
            db.session.commit()
            
            # Create notification for company
            company_user = User.query.get(internship.company_id)
            if company_user:
                notification = Notification(
                    user_id=company_user.id,
                    title="New Application Received",
                    message=f"{current_user.full_name or current_user.email} has applied for your internship: {internship.title}",
                    notification_type="application"
                )
                db.session.add(notification)
                db.session.commit()
                
                # Send email notification to company
                email_body = f"""
                <h3>New Internship Application</h3>
                <p><strong>Applicant:</strong> {current_user.full_name or current_user.email}</p>
                <p><strong>Position:</strong> {internship.title}</p>
                <p><strong>Applied Date:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                <p>Please check your dashboard to review this application.</p>
                """
                send_email(company_user.email, "New Internship Application", email_body)
            
            return jsonify({
                "success": True,
                "message": "Application submitted successfully",
                "application_id": new_application.id
            }, 201)
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 500
    
    elif request.method == "DELETE":
        try:
            data = request.get_json()
            application_id = data.get('application_id')
            
            if not application_id:
                return jsonify({"success": False, "error": "Application ID is required"}), 400
            
            # Find the application
            application = Application.query.filter_by(
                id=application_id,
                student_id=current_user.id
            ).first()
            
            if not application:
                return jsonify({"success": False, "error": "Application not found"}), 404
            
            # Store application details for notification before deleting
            internship = Internship.query.get(application.internship_id)
            company_user = User.query.get(internship.company_id) if internship else None
            
            # Delete the application
            db.session.delete(application)
            db.session.commit()
            
            # Create notification for company about withdrawal
            if internship and company_user:
                notification = Notification(
                    user_id=company_user.id,
                    title="Application Withdrawn",
                    message=f"{current_user.full_name or current_user.email} has withdrawn their application for: {internship.title}",
                    notification_type="application_withdrawn"
                )
                db.session.add(notification)
                db.session.commit()
                
                # Send email notification to company
                email_body = f"""
                <h3>Application Withdrawn</h3>
                <p><strong>Applicant:</strong> {current_user.full_name or current_user.email}</p>
                <p><strong>Position:</strong> {internship.title}</p>
                <p><strong>Withdrawn Date:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                <p>The applicant has withdrawn their application for this position.</p>
                """
                send_email(company_user.email, "Application Withdrawn", email_body)
            
            return jsonify({
                "success": True,
                "message": "Application withdrawn successfully"
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 500

# Notifications API
@app.route("/api/notifications", methods=["GET"])
@token_required
def get_notifications(current_user):
    try:
        notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
        
        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat()
            })
        
        return jsonify({
            "success": True,
            "notifications": notifications_data
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/notifications/mark-read", methods=["POST"])
@token_required
def mark_notification_read(current_user):
    try:
        data = request.get_json()
        notification_id = data.get('notification_id')
        
        if notification_id == 'all':
            # Mark all as read
            Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
            db.session.commit()
            return jsonify({"success": True, "message": "All notifications marked as read"}), 200
        else:
            # Mark specific notification as read
            notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
            if notification:
                notification.is_read = True
                db.session.commit()
                return jsonify({"success": True, "message": "Notification marked as read"}), 200
            else:
                return jsonify({"success": False, "error": "Notification not found"}), 404
                
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# AI Resume Builder API
@app.route("/api/generate-resume", methods=["POST"])
@token_required
def generate_resume(current_user):
    try:
        # This would integrate with an AI service in a real application
        # For now, we'll return a sample resume structure
        
        resume_data = {
            "success": True,
            "resume": {
                "personal_info": {
                    "name": current_user.full_name,
                    "email": current_user.email,
                    "phone": current_user.mobile,
                    "location": getattr(current_user, 'location', ''),
                    "linkedin": getattr(current_user, 'linkedin', ''),
                    "github": getattr(current_user, 'github', '')
                },
                "education": {
                    "university": current_user.college,
                    "degree": current_user.course,
                    "graduation_year": current_user.graduation_year
                },
                "skills": current_user.skills.split(',') if current_user.skills else [],
                "summary": current_user.description or "Motivated student with strong technical skills and passion for software development. Seeking internship opportunities to apply and enhance my programming abilities.",
                "projects": [
                    {
                        "title": "E-Commerce Web Application",
                        "description": "Developed a full-stack e-commerce platform with user authentication, product catalog, and payment integration.",
                        "technologies": ["Python", "Flask", "React", "PostgreSQL", "Stripe API"]
                    },
                    {
                        "title": "Task Management Mobile App", 
                        "description": "Built a cross-platform mobile application for task management with real-time synchronization.",
                        "technologies": ["JavaScript", "React Native", "Firebase", "Redux"]
                    }
                ]
            }
        }
        
        return jsonify(resume_data), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Company Profile API - Complete Fix
@app.route("/api/company/profile", methods=["GET", "PUT"])
@token_required
def company_profile(current_user):
    try:
        if current_user.user_type != 'company':
            return jsonify({"success": False, "error": "Access denied"}), 403
        
        if request.method == 'GET':
            # Return complete company profile
            profile_data = {
                "id": current_user.id,
                "email": current_user.email,
                "company_name": current_user.company_name or "",
                "industry": current_user.industry or "",
                "company_size": current_user.company_size or "",
                "website": current_user.website or "",
                "description": current_user.description or "",
                "location": current_user.location or "",
                "contact_person": current_user.contact_person or "",
                "mobile": current_user.mobile or "",
                "contact_email": current_user.email or "",  # Add this for the form
                "logo_url": current_user.profile_picture or "",
                "social_links": {
                    "linkedin": current_user.linkedin or "",
                    "twitter": getattr(current_user, 'twitter', '') or "",
                    "facebook": getattr(current_user, 'facebook', '') or "",
                    "instagram": getattr(current_user, 'instagram', '') or "",
                    "github": current_user.github or ""
                },
                "founded_year": getattr(current_user, 'founded_year', None)  # Add if you have this field
            }
            return jsonify({"success": True, "profile": profile_data}), 200
        
        # PUT - Update profile
        data = request.get_json() or {}
        print(f"Updating company profile with data: {data}")  # Debug log
        
        # Update basic company fields
        update_fields = [
            'company_name', 'industry', 'company_size', 'website', 'description',
            'location', 'contact_person', 'mobile'
        ]
        
        for field in update_fields:
            if field in data:
                value = data[field] or ""
                setattr(current_user, field, value)
                print(f"Updated {field}: {value}")
        
        # Handle founded_year separately if it exists
        if 'founded_year' in data:
            try:
                current_user.founded_year = int(data['founded_year']) if data['founded_year'] else None
            except (ValueError, TypeError):
                current_user.founded_year = None
        
        # Update social links
        if 'social_links' in data:
            social_links = data['social_links'] or {}
            current_user.linkedin = social_links.get('linkedin', '') or ""
            current_user.github = social_links.get('github', '') or ""
            
            # Add these fields to your User model if they don't exist
            if hasattr(current_user, 'twitter'):
                current_user.twitter = social_links.get('twitter', '') or ""
            if hasattr(current_user, 'facebook'):
                current_user.facebook = social_links.get('facebook', '') or ""
            if hasattr(current_user, 'instagram'):
                current_user.instagram = social_links.get('instagram', '') or ""
        
        # Update timestamp
        current_user.updated_at = datetime.datetime.utcnow()
        
        db.session.commit()
        
        # Return updated profile data
        updated_profile = {
            "company_name": current_user.company_name,
            "industry": current_user.industry,
            "company_size": current_user.company_size,
            "website": current_user.website,
            "description": current_user.description,
            "location": current_user.location,
            "contact_person": current_user.contact_person,
            "mobile": current_user.mobile,
            "contact_email": current_user.email,
            "logo_url": current_user.profile_picture or "",
            "social_links": {
                "linkedin": current_user.linkedin or "",
                "twitter": getattr(current_user, 'twitter', '') or "",
                "facebook": getattr(current_user, 'facebook', '') or "",
                "instagram": getattr(current_user, 'instagram', '') or "",
                "github": current_user.github or ""
            }
        }
        
        return jsonify({
            "success": True, 
            "message": "Profile updated successfully",
            "profile": updated_profile
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in company profile: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Company Internships - Fixed with proper error handling
@app.route("/api/company/internships", methods=["GET", "POST"])
@token_required
def company_internships(current_user):
    try:
        if current_user.user_type != 'company':
            return jsonify({"success": False, "error": "Access denied"}), 403
        
        if request.method == 'GET':
            listings = Internship.query.filter_by(company_id=current_user.id).order_by(Internship.created_at.desc()).all()
            data = []
            for internship in listings:
                # Count applications for each internship
                application_count = Application.query.filter_by(internship_id=internship.id).count()
                
                data.append({
                    "id": internship.id,
                    "title": internship.title,
                    "description": internship.description,
                    "requirements": internship.requirements,
                    "skills_required": internship.skills_required.split(',') if internship.skills_required else [],
                    "internship_type": internship.internship_type,
                    "location": internship.location,
                    "salary": internship.salary,
                    "duration": internship.duration,
                    "work_mode": internship.work_mode,
                    "start_date": internship.start_date.isoformat() if internship.start_date else None,
                    "deadline": internship.deadline.isoformat() if internship.deadline else None,
                    "responsibilities": internship.responsibilities,
                    "learning_outcomes": internship.learning_outcomes,
                    "education_level": internship.education_level,
                    "experience_level": internship.experience_level,
                    "openings": internship.openings,
                    "is_active": internship.is_active,
                    "is_published": internship.is_published,
                    "application_count": application_count,
                    "created_at": internship.created_at.isoformat()
                })
            return jsonify({"success": True, "internships": data}), 200
        
        # POST - Create new internship
        data = request.get_json() or {}
        print(f"Received internship data: {data}")  # Debug log
        
        # Required fields validation
        required_fields = ['title', 'description', 'requirements']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({"success": False, "error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        # Handle skills
        skills_val = data.get('skills_required', [])
        if isinstance(skills_val, list):
            skills_str = ','.join([skill.strip() for skill in skills_val if skill.strip()])
        else:
            skills_str = str(skills_val) if skills_val else ''
        
        # Parse dates
        start_date = None
        deadline = None
        
        if data.get('start_date'):
            try:
                start_date = datetime.datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
            except ValueError as e:
                print(f"Invalid start_date format: {e}")
        
        if data.get('deadline'):
            try:
                deadline = datetime.datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
            except ValueError as e:
                print(f"Invalid deadline format: {e}")
        
        # Create new internship
        internship = Internship(
            company_id=current_user.id,
            title=data['title'].strip(),
            description=data['description'].strip(),
            requirements=data.get('requirements', '').strip(),
            skills_required=skills_str,
            internship_type=data.get('internship_type', ''),
            location=data.get('location', ''),
            salary=data.get('stipend', data.get('salary', '')),  # Handle both 'stipend' and 'salary'
            duration=data.get('duration', ''),
            work_mode=data.get('work_mode', 'remote'),
            start_date=start_date,
            deadline=deadline,
            responsibilities=data.get('responsibilities', ''),
            learning_outcomes=data.get('learning_outcomes', ''),
            education_level=data.get('education_level', ''),
            experience_level=data.get('experience_level', ''),
            openings=data.get('openings', 1),
            is_active=True,
            is_published=True  # Auto-publish when created
        )
        
        db.session.add(internship)
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Internship posted successfully", 
            "id": internship.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in company_internships: {str(e)}")
        return jsonify({"success": False, "error": f"Failed to process internship: {str(e)}"}), 500

# Also update the PUT route for internships
@app.route("/api/company/internships/<int:internship_id>", methods=["PUT", "DELETE"])
@token_required
def company_internship_detail(current_user, internship_id):
    try:
        if current_user.user_type != 'company':
            return jsonify({"success": False, "error": "Access denied"}), 403
        
        internship = Internship.query.filter_by(id=internship_id, company_id=current_user.id).first()
        if not internship:
            return jsonify({"success": False, "error": "Internship not found"}), 404
        
        if request.method == 'DELETE':
            db.session.delete(internship)
            db.session.commit()
            return jsonify({"success": True, "message": "Internship deleted successfully"}), 200
        
        # PUT - update internship
        data = request.get_json() or {}
        
        # Update basic fields
        update_fields = ['title', 'description', 'requirements', 'internship_type', 'location', 'salary', 'duration', 'work_mode', 'responsibilities', 'learning_outcomes', 'education_level', 'experience_level']
        
        for field in update_fields:
            if field in data:
                setattr(internship, field, data[field])
        
        # Handle skills
        if 'skills_required' in data:
            sr = data['skills_required']
            internship.skills_required = ','.join(sr) if isinstance(sr, list) else (sr or '')
        
        # Handle openings
        if 'openings' in data:
            try:
                internship.openings = int(data['openings']) if data['openings'] else 1
            except (ValueError, TypeError):
                internship.openings = 1
                
        # Handle dates
        if 'start_date' in data and data['start_date']:
            try:
                internship.start_date = datetime.datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
            except ValueError:
                pass
                
        if 'deadline' in data and data['deadline']:
            try:
                internship.deadline = datetime.datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
            except ValueError:
                pass
                
        # Handle boolean fields
        if 'is_active' in data:
            internship.is_active = bool(data['is_active'])
        if 'is_published' in data:
            internship.is_published = bool(data['is_published'])
            
        internship.updated_at = datetime.datetime.utcnow()
        db.session.commit()
        
        return jsonify({"success": True, "message": "Internship updated successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating internship: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Company Applications - Enhanced with internship filtering
@app.route("/api/company/applications", methods=["GET"])
@token_required
def company_applications(current_user):
    try:
        if current_user.user_type != 'company':
            return jsonify({"success": False, "error": "Access denied"}), 403
        
        # Get internship_id filter if provided
        internship_id = request.args.get('internship_id', type=int)
        
        # Base query
        query = db.session.query(Application, Internship, User).\
            join(Internship, Application.internship_id == Internship.id).\
            join(User, Application.student_id == User.id).\
            filter(Internship.company_id == current_user.id)
        
        # Filter by specific internship if requested
        if internship_id:
            query = query.filter(Application.internship_id == internship_id)
        
        apps = query.order_by(Application.applied_date.desc()).all()
        
        data = []
        for app, internship, student in apps:
            # Parse student skills
            student_skills = []
            if student.skills:
                student_skills = [skill.strip() for skill in student.skills.split(',') if skill.strip()]
            
            data.append({
                "id": app.id,
                "status": app.status,
                "applied_date": app.applied_date.isoformat(),
                "updated_at": app.updated_at.isoformat(),
                "cover_letter": app.cover_letter or "",
                "internship": {
                    "id": internship.id,
                    "title": internship.title
                },
                "student": {
                    "id": student.id,
                    "name": student.full_name or student.email,
                    "email": student.email,
                    "college": student.college or "",
                    "course": student.course or "",
                    "skills": student_skills,
                    "resume_url": student.resume_url or "",
                    "mobile": student.mobile or "",
                    "graduation_year": student.graduation_year or "",
                    "profile_picture": student.profile_picture or ""
                }
            })
        return jsonify({"success": True, "applications": data}), 200
        
    except Exception as e:
        print(f"Error loading company applications: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Get applications for specific internship
@app.route("/api/company/internships/<int:internship_id>/applications", methods=["GET"])
@token_required
def company_internship_applications(current_user, internship_id):
    try:
        if current_user.user_type != 'company':
            return jsonify({"success": False, "error": "Access denied"}), 403
        
        # Verify the internship belongs to the company
        internship = Internship.query.filter_by(id=internship_id, company_id=current_user.id).first()
        if not internship:
            return jsonify({"success": False, "error": "Internship not found"}), 404
        
        # Get applications for this specific internship
        apps = db.session.query(Application, User).\
            join(User, Application.student_id == User.id).\
            filter(Application.internship_id == internship_id).\
            order_by(Application.applied_date.desc()).all()
        
        data = []
        for app, student in apps:
            # Parse student skills
            student_skills = []
            if student.skills:
                student_skills = [skill.strip() for skill in student.skills.split(',') if skill.strip()]
            
            data.append({
                "id": app.id,
                "status": app.status,
                "applied_date": app.applied_date.isoformat(),
                "updated_at": app.updated_at.isoformat(),
                "cover_letter": app.cover_letter or "",
                "student": {
                    "id": student.id,
                    "name": student.full_name or student.email,
                    "email": student.email,
                    "college": student.college or "",
                    "course": student.course or "",
                    "skills": student_skills,
                    "resume_url": student.resume_url or "",
                    "mobile": student.mobile or "",
                    "graduation_year": student.graduation_year or "",
                    "profile_picture": student.profile_picture or ""
                }
            })
        return jsonify({"success": True, "applications": data, "internship_title": internship.title}), 200
        
    except Exception as e:
        print(f"Error loading internship applications: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/company/applications/<int:application_id>", methods=["PUT"])
@token_required
def update_company_application(current_user, application_id):
    try:
        if current_user.user_type != 'company':
            return jsonify({"success": False, "error": "Access denied"}), 403
        
        app_rec = db.session.query(Application).\
            join(Internship, Application.internship_id == Internship.id).\
            filter(Application.id == application_id, Internship.company_id == current_user.id).first()
        
        if not app_rec:
            return jsonify({"success": False, "error": "Application not found"}), 404
        
        data = request.get_json() or {}
        if 'status' in data:
            old_status = app_rec.status
            app_rec.status = data['status']
            app_rec.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            # Create notification for student
            if old_status != data['status']:
                student = User.query.get(app_rec.student_id)
                internship = Internship.query.get(app_rec.internship_id)
                
                if student and internship:
                    notification = Notification(
                        user_id=student.id,
                        title="Application Status Updated",
                        message=f"Your application for {internship.title} at {current_user.company_name} has been {data['status']}",
                        notification_type="application_status"
                    )
                    db.session.add(notification)
                    db.session.commit()
                    
                    # Send email to student
                    email_body = f"""
                    <h3>Application Status Update</h3>
                    <p>Your application for <strong>{internship.title}</strong> at <strong>{current_user.company_name}</strong> has been updated.</p>
                    <p><strong>New Status:</strong> {data['status'].title()}</p>
                    <p>Please check your dashboard for more details.</p>
                    """
                    send_email(student.email, "Application Status Update", email_body)
            
        return jsonify({"success": True, "message": "Application updated successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating application: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Quick approve/reject endpoints
@app.route("/api/company/applications/<int:application_id>/approve", methods=["POST"])
@token_required
def approve_application(current_user, application_id):
    try:
        if current_user.user_type != 'company':
            return jsonify({"success": False, "error": "Access denied"}), 403
        
        app_rec = db.session.query(Application).\
            join(Internship, Application.internship_id == Internship.id).\
            filter(Application.id == application_id, Internship.company_id == current_user.id).first()
        
        if not app_rec:
            return jsonify({"success": False, "error": "Application not found"}), 404
        
        old_status = app_rec.status
        app_rec.status = 'approved'
        app_rec.updated_at = datetime.datetime.utcnow()
        db.session.commit()
        
        # Create notification for student
        student = User.query.get(app_rec.student_id)
        internship = Internship.query.get(app_rec.internship_id)
        
        if student and internship:
            notification = Notification(
                user_id=student.id,
                title="Application Approved!",
                message=f"Congratulations! Your application for {internship.title} at {current_user.company_name} has been approved.",
                notification_type="application_status"
            )
            db.session.add(notification)
            db.session.commit()
            
            # Send email to student
            email_body = f"""
            <h3>Application Approved!</h3>
            <p>Congratulations! Your application for <strong>{internship.title}</strong> at <strong>{current_user.company_name}</strong> has been approved.</p>
            <p>The company will contact you soon with further details.</p>
            <p>Best regards,<br>SkillBridge Team</p>
            """
            send_email(student.email, "Application Approved - SkillBridge", email_body)
        
        return jsonify({"success": True, "message": "Application approved successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error approving application: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/company/applications/<int:application_id>/reject", methods=["POST"])
@token_required
def reject_application(current_user, application_id):
    try:
        if current_user.user_type != 'company':
            return jsonify({"success": False, "error": "Access denied"}), 403
        
        app_rec = db.session.query(Application).\
            join(Internship, Application.internship_id == Internship.id).\
            filter(Application.id == application_id, Internship.company_id == current_user.id).first()
        
        if not app_rec:
            return jsonify({"success": False, "error": "Application not found"}), 404
        
        old_status = app_rec.status
        app_rec.status = 'rejected'
        app_rec.updated_at = datetime.datetime.utcnow()
        db.session.commit()
        
        # Create notification for student
        student = User.query.get(app_rec.student_id)
        internship = Internship.query.get(app_rec.internship_id)
        
        if student and internship:
            notification = Notification(
                user_id=student.id,
                title="Application Status Update",
                message=f"Your application for {internship.title} at {current_user.company_name} has been rejected.",
                notification_type="application_status"
            )
            db.session.add(notification)
            db.session.commit()
            
            # Send email to student
            email_body = f"""
            <h3>Application Status Update</h3>
            <p>We regret to inform you that your application for <strong>{internship.title}</strong> at <strong>{current_user.company_name}</strong> has been rejected.</p>
            <p>Don't be discouraged! Keep applying to other opportunities that match your skills.</p>
            <p>Best regards,<br>SkillBridge Team</p>
            """
            send_email(student.email, "Application Status Update - SkillBridge", email_body)
        
        return jsonify({"success": True, "message": "Application rejected successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error rejecting application: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Company Logo Upload - Fixed
@app.route("/api/company/upload-logo", methods=["POST"])
@token_required
def upload_company_logo(current_user):
    try:
        if current_user.user_type != 'company':
            return jsonify({"success": False, "error": "Access denied"}), 403
        
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        # Check file type
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        file_extension = os.path.splitext(file.filename.lower())[1]
        if file_extension not in allowed_extensions:
            return jsonify({"success": False, "error": "Only image files (JPG, PNG, GIF, WEBP) are allowed."}), 400
        
        # Check file size (5MB limit)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        if file_size > 5 * 1024 * 1024:
            return jsonify({"success": False, "error": "File size must be less than 5MB."}), 400
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            file,
            folder=f"skillbridge/company_logos/{current_user.id}",
            public_id=f"logo_{current_user.id}_{uuid.uuid4().hex[:8]}",
            overwrite=True,
            quality="auto",
            fetch_format="auto"
        )
        
        # Save URL to database
        current_user.profile_picture = upload_result['secure_url']
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Company logo uploaded successfully",
            "image_url": upload_result['secure_url']
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error uploading company logo: {str(e)}")
        return jsonify({"success": False, "error": f"Upload failed: {str(e)}"}), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Create sample internships on startup
        create_sample_internships()
    app.run(debug=True)