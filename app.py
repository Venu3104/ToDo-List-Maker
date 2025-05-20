from flask import Flask, render_template, request, redirect, jsonify, session, flash, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from functools import wraps
import secrets
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure random value!
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "todo.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Todo(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    desc = db.Column(db.String(500), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def __repr__(self):
        return f"{self.sno} - {self.title}"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'warning')
            return redirect(url_for('register'))
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')
            return redirect(url_for('hello_world'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    reset_link = None
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash('Please enter your email.', 'danger')
            return render_template('forgot_password.html', reset_link=reset_link)
        user = User.query.filter_by(email=email).first()
        if user:
            s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
            token = s.dumps(email, salt='password-reset-salt')
            reset_link = url_for('reset_password', token=token, _external=True)
            flash('Password reset link generated below.', 'success')
        else:
            flash('No account found with that email.', 'danger')
    return render_template('forgot_password.html', reset_link=reset_link)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)  # 1 hour expiry
    except SignatureExpired:
        flash("Reset link expired.", "danger")
        return redirect(url_for('forgot_password'))
    except BadSignature:
        flash("Invalid reset link.", "danger")
        return redirect(url_for('forgot_password'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Invalid reset link.", "danger")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        if not password:
            flash("Password is required.", "danger")
            return render_template('reset_password.html')
        user.set_password(password)
        db.session.commit()
        flash("Password reset successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

@app.route("/", methods=["GET", "POST"])
@login_required
def hello_world():
    user_id = session.get('user_id')
    if request.method == "POST":
        title = request.form.get("title")
        desc = request.form.get("desc")
        todo = Todo(title=title, desc=desc, user_id=user_id)
        db.session.add(todo)
        db.session.commit()
    todos = Todo.query.filter_by(user_id=user_id).all()
    return render_template("index.html", todos=todos)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/delete/<int:sno>")
@login_required
def delete(sno):
    user_id = session.get('user_id')
    todo = Todo.query.filter_by(sno=sno, user_id=user_id).first()
    if todo:
        db.session.delete(todo)
        db.session.commit()
    return redirect("/")

@app.route("/update/<int:sno>", methods=["GET", "POST"])
@login_required
def update(sno):
    user_id = session.get('user_id')
    todo = Todo.query.filter_by(sno=sno, user_id=user_id).first()
    if not todo:
        flash("Todo not found or not authorized.", "danger")
        return redirect("/")
    if request.method == "POST":
        title = request.form.get("title")
        desc = request.form.get("desc")
        todo.title = title
        todo.desc = desc
        db.session.commit()
        return redirect("/")
    return render_template("update.html", todo=todo)

@app.route("/search")
@login_required
def search():
    user_id = session.get('user_id')
    query = request.args.get("q", "")
    todos = Todo.query.filter(
        ((Todo.title.contains(query)) | (Todo.desc.contains(query))) & (Todo.user_id == user_id)
    ).all()
    results = [
        {
            "sno": todo.sno,
            "title": todo.title,
            "desc": todo.desc,
            "date_created": todo.date_created.strftime("%Y-%m-%d %H:%M")
        }
        for todo in todos
    ]
    return jsonify(results)

@app.route("/download-db")
def download_db():
    db_path = os.path.join(os.getcwd(), 'todo.db')
    return send_file(db_path, as_attachment=True)

@app.context_processor
def inject_now():
    return {'now': datetime.now}

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=8000)