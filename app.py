from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "todo.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Todo(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    desc = db.Column(db.String(500), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"{self.sno} - {self.title}"

@app.route("/" ,methods=["GET", "POST"])
def hello_world():
    if request.method == "POST":
        title = request.form.get("title")
        desc = request.form.get("desc")
        todo = Todo(title=title, desc=desc)
        db.session.add(todo)
        db.session.commit()
    todos = Todo.query.all()
    return render_template("index.html", todos=todos)

@app.route("/about")
def about():
    return render_template("about.html")

# @app.route("/show")
# def Products():
#     todos = Todo.query.all()
#     print(todos)
#     return "<p>This is a products page.</p>"

@app.route("/delete/<int:sno>")
def delete(sno):
    todo = Todo.query.filter_by(sno=sno).first()  # Find the row by sno
    if todo:
        db.session.delete(todo)  # Delete the row
        db.session.commit()  # Commit the changes
    return redirect("/")

@app.route("/update/<int:sno>", methods=["GET", "POST"])
def update(sno):
    todo = Todo.query.filter_by(sno=sno).first()
    if request.method == "POST":
        title = request.form.get("title")
        desc = request.form.get("desc")
        todo.title = title
        todo.desc = desc
        db.session.commit()
        return redirect("/")
    return render_template("update.html", todo=todo)


    from flask import jsonify

@app.route("/search")
def search():
    query = request.args.get("q", "")
    todos = Todo.query.filter(
        (Todo.title.contains(query)) | (Todo.desc.contains(query))
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




@app.context_processor
def inject_now():
    return {'now': datetime.now}



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=8000)