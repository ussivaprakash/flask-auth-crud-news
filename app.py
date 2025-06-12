from flask import Flask, render_template, redirect, url_for, request ,flash
from werkzeug.security import generate_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, News
from flask import session
import os
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
import re



app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///User.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads' 
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
migrate = Migrate(app, db)



login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    author_id = request.args.get('author_id', type=int)
    search = request.args.get('search')
    query = News.query

    if author_id:
        query = query.filter_by(user_id=author_id)
    if search:
        query = query.filter(News.title.ilike(f"%{search}%"))

    news = query.order_by(News.created_at.desc()).all()
    users = User.query.all()
    return render_template('news_list.html', news_list=news, users=users, author_id=author_id)

# signup
@app.route('/signup', methods=['GET', 'POST'])  
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password_hash')
        confirm = request.form.get('confirm_password')
        
        # Validation
        if not full_name or not email or not password or not confirm:
            return redirect(url_for('signup'))

        if password != confirm:
            return redirect(url_for('signup'))

        if (len(password) < 8 or
             not re.search(r'[A-Z]', password) or
             not re.search(r'[a-z]', password) or
             not re.search(r'\d', password) or
             not re.search(r'[!@#$%^&*(),.?":{}|<>]', password)):
            return redirect(url_for('signup'))
        
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
           
            return redirect(url_for('signup')) 

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return redirect(url_for('signup'))

        # Create user
        new_user = User(
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password)
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('signup.html')
@app.route('/login', methods=['GET', 'POST'])

def login():
    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')
        # Validation
        user = User.query.filter_by(email=email).first()
        remember = True if request.form.get('remember') else False
         # <-- Use .first() to get a single user object
        if user and user.check_password(password):
            login_user(user) 
            login_user(user, remember= remember) # <-- This is important!
            session['user_id'] = user.id
            session['user_email'] = user.email
            return redirect(url_for('home'))
        return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/dashboard') 
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
        logout_user()
        session.clear()     
        return redirect(url_for('signup'))  

@app.route('/profile')
@login_required
def profile():
    blog_count = News.query.filter_by(user_id=current_user.id).count()
    current_user.blog_count = blog_count
    return render_template('profile.html', user=current_user)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')

        if full_name:
            current_user.full_name = full_name
        if email:
            current_user.email = email
        if password:
            current_user.password_hash = generate_password_hash(password)

        if 'profile_pic' in request.files:
            pic = request.files['profile_pic']
            if pic and pic.filename:
                filename = secure_filename(pic.filename)
                pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.profile_pic = filename

        db.session.commit()
        return redirect(url_for('profile'))
    return render_template('edit_profile.html', user=current_user)

@app.route('/news/create', methods=['GET', 'POST'])
@login_required
def create_news():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        news = News(title=title, content=content, author=current_user)
        db.session.add(news)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('create_news.html')

@app.route('/news/<int:news_id>')
def view_news(news_id):
    news = News.query.get_or_404(news_id)
    return render_template('news_detail.html', news=news)


@app.route('/news/<int:news_id>/update', methods=['GET', 'POST'])
@login_required
def update(news_id):
    news=News.query.get_or_404(news_id)
    if request.method == 'POST':
        news.title = request.form['title']
        news.content = request.form['content']
        db.session.commit()
        return redirect(url_for('view_news', news_id=news.id))
    return render_template('update_news.html', news=news)
   

@app.route('/news/<int:news_id>/delete', methods=['POST'])
@login_required
def delete_news(news_id):
    news = News.query.get_or_404(news_id)
    db.session.delete(news)
    db.session.commit() 
    return redirect(url_for('home'))
            



if __name__ == '__main__':
    app.run(debug=True)

