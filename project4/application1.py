import os, json

from flask import Flask, session, redirect, render_template, request, jsonify, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from werkzeug.security import check_password_hash, generate_password_hash

import requests

from required import login_required

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


carrito=[]

@app.route("/")
@login_required # Calls the decorator from required.py using @, AKA index = login_required(index)
def index():


    userid=session.get("user_id")
    username= (db.execute("select username from users where user_id=:userid",
                        {"userid": userid})).fetchone()
    category=(db.execute("select distinct categoria from productos")).fetchall()



    return render_template("index.html",Category=category,user=username[0])

#login

@app.route("/login", methods=["GET", "POST"])
def login():

    session.clear() # Forget old sessions

    username = request.form.get("username")
    if request.method=="POST":
        if not request.form.get("username"):
            return render_template("login.html",message="Invalid credentials")
        elif not request.form.get("password"):
            return render_template("login.html", message="Invalid credentials")


        query = db.execute("SELECT * FROM users WHERE username = :username",
                            {"username": username})

        # Fetch row to check if username
        result = query.fetchone()
        if result == None or not check_password_hash(result[2], request.form.get("password")):
            return render_template("login.html", message="Invalid username or password")

        session["user_id"] = result[0]
        session["user_name"] = result[1]

        # Redirect user to index page
        return redirect("/")



    return render_template("login.html")



# Register user function
@app.route("/signin", methods=["GET", "POST"])
def register():

    # Clear session before any new user
    session.clear()

    if request.method == "POST":

        # Render error.html in case of not username
        if not request.form.get("username"):
            return render_template("signin.html", message="Please enter a username")

        # Query database for username
        user = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username":request.form.get("username")}).fetchone()

        # Check if username already exist
        if user:
            return render_template("signin.html", message="username already exist")

        # Check if password was submitted
        elif not request.form.get("password"):
            return render_template("signin.html", message="Please enter a password")

        # Check if password confirmation form was filled
        elif not request.form.get("password2"):
            return render_template("signin.html", message="Please confirm password")

        # Check if passwords are equal
        elif not request.form.get("password") == request.form.get("password2"):
            return render_template("signin.html", message="passwords did not match")

        # Store hashed password
        hashedPass = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                            {"username":request.form.get("username"),
                             "password":hashedPass})

        # Commit
        db.commit()

        # Redirect user to login page
        return render_template("login.html", message="Registered. You can log in now.")

    else:
        return render_template("signin.html")


@app.route("/logout")
def logout():

    session.clear()
    return render_template("login.html", message="Logged out.")


@app.route("/category/<element>", methods=['GET','POST'])
@login_required
def category(element):

    userid=session.get("user_id")
    username= (db.execute("select username from users where user_id=:userid",
                            {"userid": userid})).fetchone()
    category=(db.execute("select distinct categoria from productos")).fetchall()

    consulta="select * from productos where categoria='"+element+"'"
    query=db.execute(consulta)
    products=query.fetchall()
    return render_template("menu.html",productlist=products,Category=category,user=username[0])

@app.route("/carrito/<codigo>", methods=['GET','POST'])
@login_required
def llenarcarrito(codigo):

    consulta1= (db.execute("select * from productos where codigo=:codigo",
                            {"codigo": codigo})).fetchall()
    userid=session.get("user_id")
    username= (db.execute("select username from users where user_id=:userid",
                            {"userid": userid})).fetchone()
    category=(db.execute("select distinct categoria from productos")).fetchall()

    consulta="select * from productos where categoria=:cate"
    query=db.execute(consulta,{"cate":consulta1[0][3]})
    products=query.fetchall()
    carrito.append(consulta1)
    valor_total=precio_total()


    return render_template("menu.html",carrito=carrito,total=valor_total,productlist=products,Category=category,user=username[0])

def precio_total():
    total=0
    for elemento in carrito:
        total=total+elemento[0][2]
    return(total)

@app.route("/delete/<codigo>", methods=['GET','POST'])
@login_required

def vaciarcarrito(codigo):
    consulta1=(db.execute("select categoria from productos where codigo=:codigo",
                            {"codigo": codigo})).fetchone()
    userid=session.get("user_id")
    username= (db.execute("select username from users where user_id=:userid",
                            {"userid": userid})).fetchone()
    category=(db.execute("select distinct categoria from productos")).fetchall()

    consulta="select * from productos where categoria=:cate"
    query=db.execute(consulta,{"cate":consulta1[0]})
    products=query.fetchall()
    index=0
    cont=0
    for elemento in carrito:
        if codigo==elemento[0][0]:
            index=cont
            carrito.pop(index)
            break
        cont+=1
    valor_total=precio_total()
    return render_template("menu.html",carrito=carrito,total=valor_total,productlist=products,Category=category,user=username[0])


@app.route("/myorder", methods=['GET','POST'])
@login_required
def my_orders():

    userid=session.get("user_id")
    username= (db.execute("select username from users where user_id=:userid",
                            {"userid": userid})).fetchone()
    category=(db.execute("select distinct categoria from productos")).fetchall()

    valor_total=precio_total()
    compras=(db.execute("select id_fact,username,total from factura inner join users on id_user=user_id where user_id=:userid",
                            {"userid": userid})).fetchall()
    if len(carrito)>0:
        return render_template("my_orders.html",carrito=carrito,total=valor_total,Category=category,user=username[0],compras=compras)

    return render_template("my_orders.html",total=valor_total,Category=category,user=username[0],compras=compras)

@app.route("/confirmorder", methods=['GET','POST'])
@login_required
def confirmed():
    userid=session.get("user_id")
    valor_total=precio_total()

    db.execute("INSERT INTO factura(total,id_user) VALUES (:total,:id_user)",
    {"total":valor_total,"id_user":userid})
    db.commit()
    carrito.clear()
    return index()
    #return render(request,"my_orders.html",context)
