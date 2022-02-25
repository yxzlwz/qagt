import hashlib
import time

import lightmysql
from flask import *

app = Flask(__name__)
app.secret_key = "QABBQ"
mysql = lightmysql.Connect("alimysql.yixiangzhilv.com",
                           "yxzl",
                           "yxzl@Danny20070601",
                           "qabbq",
                           pool_size=3)


class Users:
    users = {}

    def __init__(self):
        data = [
            "id", "name", "password", "email", "real_name", "real_name_md5",
            "sex", "grade", "introduction"
        ]
        temp = mysql.select("users", data)
        for i in temp:
            user = {data[j]: i[j] for j in range(len(data))}
            self.users[i[0]] = user
        return

    def add(self, name, password):
        for i, j in self.users.items():
            if j["name"] == name:
                return "用户名已存在"
        user = {"name": name, "password": password}
        user["tags"] = "无认证信息"
        user["sex"] = user["grade"] = "保密"
        user["real_name"] = user["email"] = ""
        mysql.insert("users", user)
        user["id"] = mysql.select("users", ["id"], {"name": name})[0][0]
        self.users[user["id"]] = user
        return user

    def update(self, num, values):
        if values["real_name"]:
            values["real_name_md5"] = get_md5(values["real_name"])
        mysql.update("users", values, {"id": num})
        data = [
            "id", "name", "password", "email", "real_name", "real_name_md5",
            "sex", "grade", "introduction"
        ]
        temp = mysql.select("users", data, {"id": num})[0]
        user = {data[j]: temp[j] for j in range(len(data))}
        self.users[num] = user
        return user

    def get_by_id(self, num):
        return self.users.get(num) or None

    def get_by_name(self, name):
        for i in self.users.values():
            if i["name"] == name:
                return i
        return None


users = Users()


def get_md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def format_time(s):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s))


def info_init():
    session["ip"] = request.headers.get(
        "Ali-Cdn-Real-Ip") or request.remote_addr


@app.route("/user/login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")
        if name and password:
            user = users.get_by_name(name)
            if user:
                if user["password"] == password:
                    session["user"] = user
                    return "Success"
                else:
                    return "密码错误"
            else:
                session["user"] = users.add(name, password)
                return "Success"
        else:
            return "用户名或密码不能为空"
    return render_template("login.html")


@app.route("/user/logout")
def user_logout():
    session.clear()
    return redirect("/")


@app.route("/")
def index():
    info_init()
    _articles = mysql.select("articles", limit="30")
    articles = []
    for i in _articles:
        articles.append({
            "id": i[0],
            "from": i[1],
            "title": i[2],
            "content": i[3],
            "time": format_time(i[4]),
            "writer": users.get_by_id(i[1])
        })
    return render_template("index.html", articles=articles[::-1])


@app.route("/user/<int:user_id>")
def user_page(user_id):
    info_init()
    if users.get_by_id(user_id) is None:
        abort(404)
    _articles = mysql.select("articles",
                             condition={"from": user_id},
                             limit="30")
    articles = []
    for i in _articles:
        articles.append({
            "id": i[0],
            "from": i[1],
            "title": i[2],
            "content": i[3],
            "time": format_time(i[4]),
            "writer": users.get_by_id(i[1])
        })
    return render_template("user_page.html",
                           owner=users.get_by_id(user_id),
                           articles=articles[::-1])


@app.route("/article/write", methods=["GET", "POST"])
def article_writing():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if request.method == "POST":
        if request.args["update"] == "true":
            mysql.update(
                "articles", {
                    "title": request.form["title"],
                    "content": request.form["content"],
                    "time": int(time.time()),
                }, {"id": request.args["id"]})
        else:
            mysql.insert(
                "articles", {
                    "from": session["user"]["id"],
                    "title": request.form["title"],
                    "content": request.form["content"],
                    "time": int(time.time())
                })
        return str(
            mysql.select("articles",
                         condition={
                             "from": session["user"]["id"],
                             "title": request.form["title"],
                             "content": request.form["content"]
                         })[-1][0])
    else:
        if request.args.get("id") and request.args["id"].isdigit():
            data = mysql.select("articles", ["from", "title", "content", "id"],
                                {"id": int(request.args["id"])})[0]
            if session["user"]["id"] == data[0]:
                data = {
                    "from": data[0],
                    "title": data[1],
                    "content": data[2],
                    "id": data[3]
                }
                return render_template("article-writing.html", data=data)
        return render_template("article-writing.html", data={})


@app.route("/article/<int:atc_id>", methods=["GET", "POST"])
def article_page(atc_id):
    info_init()
    if request.method == "POST":
        if not session.get("user"):
            return redirect("/user/login?from=" + request.url)
        mysql.insert(
            "comments", {
                "from": session.get("user")["id"],
                "under": atc_id,
                "content": request.form["comment"],
                "time": int(time.time())
            })
        return redirect("/article/%d" % atc_id)
    _article = mysql.select("articles", ["from", "title", "content", "time"],
                            {"id": atc_id})
    if not _article:
        abort(404)
    else:
        _article = _article[0]
    article = {
        "id": atc_id,
        "from": _article[0],
        "title": _article[1],
        "content": _article[2],
        "time": time.strftime("%Y年%m月%d日 %H:%M:%S",
                              time.localtime(_article[3]))
    }
    _comments = mysql.select("comments",
                             target=["from", "content", "time"],
                             condition={"under": atc_id})
    comments = []
    for i in _comments:
        comments.append({
            "from":
            users.get_by_id(i[0]),
            "content":
            i[1],
            "time":
            time.strftime("%Y年%m月%d日 %H:%M:%S", time.localtime(i[2]))
        })
    return render_template("article.html",
                           article=article,
                           comments=comments,
                           writer=users.get_by_id(article["from"]),
                           owner=users.get_by_id(article["from"]))


@app.route("/user/edit", methods=["GET", "POST"])
def edit_information():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if request.method == "POST":
        values = request.form.to_dict()
        if values["sex"] not in ["男", "女"]:
            values["sex"] = "保密"
        session["user"] = users.update(session["user"]["id"], values)
        flash("信息修改成功！")
        return redirect("/user/edit")
    else:
        return render_template("edit_information.html")


@app.route("/test")
def test():
    return render_template("edit_user_info.html")


@app.route("/404")
@app.errorhandler(404)
def error_404(error):
    return render_template("404.html")


@app.context_processor
def default():
    return {
        "user": session.get("user"),
        "title": "QA",
        "logined": bool(session.get("user"))
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7399, debug=True)
