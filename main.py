from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author_name = db.Column(db.String(80), nullable=False, default='匿名用戶')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class RegistrationKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    used = db.Column(db.Boolean, default=False)
    used_by = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime, nullable=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/blog')
def blog():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('blog.html', posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('登入成功！', 'success')
            return redirect(url_for('blog'))
        else:
            flash('用戶名或密碼錯誤', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        registration_key = request.form['registration_key']
        
        key_obj = RegistrationKey.query.filter_by(key=registration_key, used=False).first()
        if not key_obj:
            flash('註冊密鑰無效或已被使用', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('用戶名已存在', 'error')
            return render_template('register.html')
        
        if not username or not password:
            flash('用戶名和密碼不能為空', 'error')
            return render_template('register.html')
        
        key_obj.used = True
        key_obj.used_by = username
        key_obj.used_at = datetime.utcnow()
        
        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        flash('註冊成功！請登入', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('已登出', 'info')
    return redirect(url_for('blog'))

@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        flash('請先登入', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        if not title or not content:
            flash('標題和內容不能為空', 'error')
            return render_template('create_post.html')
        
        post = Post(
            title=title,
            content=content,
            user_id=session['user_id']
        )
        db.session.add(post)
        db.session.commit()
        
        flash('文章發表成功！', 'success')
        return redirect(url_for('blog'))
    
    return render_template('create_post.html')

@app.route('/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.desc()).all()
    return render_template('post_detail.html', post=post, comments=comments)

@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    content = request.form['content']
    author_name = request.form.get('author_name', '匿名用戶')
    
    if not content:
        flash('留言內容不能為空', 'error')
        return redirect(url_for('view_post', post_id=post_id))
    
    comment = Comment(
        content=content,
        author_name=author_name if author_name else '匿名用戶',
        post_id=post_id
    )
    db.session.add(comment)
    db.session.commit()
    
    flash('留言成功！', 'success')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/delete_post/<int:post_id>')
def delete_post(post_id):
    if 'user_id' not in session:
        flash('請先登入', 'error')
        return redirect(url_for('login'))
    
    post = Post.query.get_or_404(post_id)
    if post.user_id != session['user_id']:
        flash('您沒有權限刪除此文章', 'error')
        return redirect(url_for('blog'))
    
    db.session.delete(post)
    db.session.commit()
    flash('文章已刪除', 'success')
    return redirect(url_for('blog'))
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, host='0.0.0.0', port=5002)
