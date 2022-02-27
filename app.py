import hashlib
import os
import time

import lightmysql
from flask import *

app = Flask(__name__)
app.secret_key = "QABBQ"
thisDir = os.path.dirname(os.path.abspath(__file__))
mysql = lightmysql.Connect("192.168.31.186",
                           "yxzl",
                           "yxzl@Danny20070601",
                           "qagt",
                           pool_size=5)


class Users:
    users = {}
    blacklist = []
    data = [
        "id", "name", "password", "email", "real_name", "real_name_md5", "sex",
        "grade", "introduction", "tags", "admin"
    ]

    def __init__(self):
        temp = mysql.select("users", self.data)
        for i in temp:
            user = {self.data[j]: i[j] for j in range(len(self.data))}
            self.users[i[0]] = user
        return

    def add(self, name, password):
        for i, j in self.users.items():
            if j["name"] == name:
                return "用户名已存在"
        user = {"name": name, "password": password}
        user["tags"] = "无认证信息"
        user["sex"] = user["grade"] = "保密"
        user["introduction"] = user["real_name"] = user["email"] = ""
        mysql.insert("users", user)
        user["id"] = mysql.select("users", ["id"], {"name": name})[0][0]
        self.users[user["id"]] = user
        return user

    def update(self, num, values):
        if values["real_name"]:
            values["real_name_md5"] = get_md5(values["real_name"])
        mysql.update("users", values, {"id": num})
        temp = mysql.select("users", self.data, {"id": num})[0]
        user = {self.data[j]: temp[j] for j in range(len(self.data))}
        self.users[num] = user
        return user

    def get_by_id(self, num):
        return self.users.get(num) or None

    def get_by_name(self, name):
        for i in self.users.values():
            if i["name"] == name:
                return i
        return None

    def flush(self, num):
        temp = mysql.select("users", self.data, {"id": num})[0]
        user = {self.data[j]: temp[j] for j in range(len(self.data))}
        self.users[num] = user
        return user


class Notices:
    notices = {}

    def add(self, user, content, url, _time=""):
        user = int(user)
        if not url.startswith("http"):
            url = "https://qa.yxzl.top" + url
        _time = _time or format_time(int(time.time()))
        if not self.notices.get(user):
            self.notices[user] = [[content, _time, url]]
        elif self.notices[user][-1][0] != content:
            self.notices[user].append([content, _time, url])
            if len(self.notices[user]) > 10:
                self.notices[user].pop(0)

    def get(self, user):
        user = int(user)
        return self.notices.get(user) or []


class Articles:
    articles = {}
    cnt = 0
    cnts = {}

    def __init__(self):
        self.cnt = int(mysql.run_code("SELECT COUNT(id) FROM articles;")[0][0])

    def get(self, num):
        num = int(num)
        if self.articles.get(num):
            return self.articles[num]
        else:
            return self.reget(num)

    def reget(self, num):
        data = mysql.select("articles", condition={"id": num})[0]
        self.articles[num] = {
            "id": num,
            "from": data[1],
            "title": data[2],
            "content": data[3],
            "time": data[4]
        }
        return self.articles[num]

    def get_user_atcs(self, user):
        user = int(user)
        if self.cnts.get(user):
            return self.cnts[user]
        else:
            self.cnts[user] = mysql.run_code(
                f"SELECT COUNT(id) FROM articles WHERE `from`={user};")[0][0]
            return self.cnts[user]


users = Users()
notices = Notices()
articles = Articles()
infos = {"上次数据更新时间戳": 0}
start_info = {"time": int(time.time()), "request_cnt": 0}


def get_md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def format_time(s):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s))


def info_init():
    global start_info
    start_info["request_cnt"] += 1
    session["ip"] = request.headers.get(
        "Ali-Cdn-Real-Ip") or request.remote_addr
    if session.get("user"):
        if session["user"]["id"] in users.blacklist:
            abort(410)
        elif session["user"].get("admin"):
            session["user"] = users.get_by_id(session["user"]["id"])


@app.route("/user/login", methods=["GET", "POST"])
def user_login():
    info_init()
    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")
        if name and password:
            user = users.get_by_name(name)
            if user:
                if user["id"] in users.blacklist or user["password"] == "封号":
                    return "用户已被封禁"
                elif user["password"] == password:
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


@app.route("/dashboard")
def dashboard():
    global infos
    if infos["上次数据更新时间戳"] < time.time() - 600:
        infos["注册用户数"] = mysql.run_code("SELECT COUNT(id) FROM users;")[0][0]
        infos["文章数"] = mysql.run_code("SELECT COUNT(id) FROM articles;")[0][0]
        articles.cnt = infos["文章数"]
        infos["评论数"] = mysql.run_code("SELECT COUNT(id) FROM comments;")[0][0]
        infos["管理员用户数"] = mysql.run_code(
            "SELECT COUNT(id) FROM users WHERE `admin`=1 OR `admin`=2;")[0][0]
        infos["被禁止首页列出的贴子数(隐藏级别为1)"] = mysql.run_code(
            "SELECT COUNT(id) FROM articles WHERE `hide`=1;")[0][0]
        infos["被禁止列出的贴子数(隐藏级别为2)"] = mysql.run_code(
            "SELECT COUNT(id) FROM articles WHERE `hide`=2;")[0][0]
        infos["置顶贴子数"] = mysql.run_code(
            "SELECT COUNT(id) FROM articles WHERE `top`=1;")[0][0]
        infos["置顶评论数"] = mysql.run_code(
            "SELECT COUNT(id) FROM comments WHERE `top`=1;")[0][0]
        infos["未处理举报数"] = mysql.run_code(
            "SELECT COUNT(id) FROM reports;")[0][0]
        infos["上次数据更新时间戳"] = time.time()
        infos["上次数据更新时间"] = format_time(infos["上次数据更新时间戳"])
        infos["本次服务器启动时间"] = format_time(start_info["time"])
    t = int(time.time() - start_info["time"])
    infos[
        "本次启动稳定运行时长（实时）"] = f"{t // 86400}天{t % 86400 // 3600}小时{t % 3600 // 60}分钟{t % 60}秒"
    infos["本次启动后总请求数（实时）"] = start_info["request_cnt"]
    return render_template("dashboard.html", data=infos)


@app.route("/")
def index():
    info_init()
    page = int(request.args.get("page") or 1)
    if request.args.get("hide") == "false":
        _article = mysql.run_code(
            f"SELECT * FROM articles ORDER BY `id` DESC LIMIT {(page - 1) * 15}, 15;"
        )
    else:
        _article = mysql.run_code(
            f"SELECT * FROM articles WHERE `hide`=0 OR `hide` IS NULL ORDER BY `id` DESC LIMIT {(page - 1) * 15}, 15;"
        )
    _top = mysql.select("articles", condition={"top": 1})
    article = []
    top = []
    for i in (_article + _top):
        t = {
            "id": i[0],
            "from": i[1],
            "title": i[2],
            "content": i[3],
            "time": format_time(int(i[4])),
            "writer": users.get_by_id(i[1]),
            "top": i[5]
        }
        if i[5]:
            t["title"] = "【置顶】" + t["title"]
            if t not in top:
                top.append(t)
        else:
            article.append(t)
    article = top + article
    return render_template("index.html",
                           articles=article,
                           page=page,
                           pages=articles.cnt // 15 + 1)


@app.route("/user/<int:user_id>")
def user_page(user_id):
    info_init()
    if users.get_by_id(user_id) is None:
        abort(404)
    page = int(request.args.get("page") or 1)
    if request.args.get("hide") == "false":
        _article = mysql.run_code(
            f"SELECT * FROM articles WHERE `from`={user_id} ORDER BY `id` DESC LIMIT {(page - 1) * 15}, 15;"
        )
    else:
        _article = mysql.run_code(
            f"SELECT * FROM articles WHERE `from`={user_id} AND (`hide`<=1 OR `hide` IS NULL) ORDER BY `id` DESC LIMIT {(page - 1) * 15}, 15;"
        )
    _top = mysql.select("articles", condition={"top": 1, "from": user_id})
    article = []
    top = []
    for i in (_article + _top):
        t = {
            "id": i[0],
            "from": i[1],
            "title": i[2],
            "content": i[3],
            "time": format_time(int(i[4])),
            "writer": users.get_by_id(i[1]),
            "top": i[5]
        }
        if i[5]:
            t["title"] = "【置顶】" + t["title"]
            if t not in top:
                top.append(t)
        else:
            article.append(t)
    article = top + article
    return render_template("user_page.html",
                           owner=users.get_by_id(user_id),
                           articles=article,
                           page=page,
                           pages=articles.get_user_atcs(user_id) // 15 + 1)


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
            articles.reget(request.args["id"])
            return request.args["id"]
        mysql.insert(
            "articles", {
                "from": session["user"]["id"],
                "title": request.form["title"],
                "content": request.form["content"],
                "time": int(time.time())
            })
        articles.cnt += 1
        articles.get_user_atcs(session["user"]["id"])
        articles.cnts[session["user"]["id"]] += 1
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


@app.route("/article/delete/<int:atc_id>")
def article_delete(atc_id):
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    atc = articles.get(atc_id)
    if atc.get("from") != session["user"]["id"]:
        abort(403)
    try:
        mysql.delete("articles", {"id": atc_id})
        articles.cnt -= 1
        articles.articles.pop(atc_id)
        flash("删除成功！")
    except Exception as e:
        flash(f"删除失败！\n<br />\n{e}")
    return redirect(f"/user/{session['user']['id']}")


@app.route('/image-upload', methods=['POST'])
def upload():
    info_init()
    f = request.files.get('file')
    name = f"{time.time()}_{f.filename}"
    f.save(f"{thisDir}/static/article_images/{name}")
    return name


@app.route("/notice")
def make_notice():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    to = request.args["to"]
    at = request.args["at"]
    if at == "article":
        notices.add(
            to,
            f"{session['user']['name']}在文章：{articles.get(request.args['atc'])['title']}下提到了你",
            f"/article/{request.args['atc']}")
    return "Success"


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
        notices.add(
            articles.get(atc_id)["from"],
            f"{session['user']['name']}评论了你的文章：{articles.get(atc_id)['title']}",
            f"/article/{atc_id}")
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
                             target=["from", "content", "time", "top"],
                             condition={"under": atc_id})
    comment = []
    top = []
    for i in _comments:
        comment.append({
            "from": users.get_by_id(i[0]),
            "content": i[1],
            "time": format_time(i[2]),
            "top": i[3]
        })
        if i[3]:
            top.append(comment[-1])
    return render_template("article.html",
                           article=article,
                           comments=comment,
                           tops=top,
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


@app.route("/flush/user/<int:user_id>")
def flush_user(user_id):
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if not session["user"]["admin"]:
        abort(403)
    users.flush(user_id)
    return "OK"


@app.route("/report/article/<int:atc_id>")
def report_article(atc_id):
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    mysql.insert("reports", {
        "from": session["user"]["id"],
        "atc_id": atc_id,
        "time": int(time.time())
    })
    flash("举报成功！")
    return redirect("/article/%d" % atc_id)


@app.route("/admin")
def admin_index():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if not session["user"]["admin"]:
        abort(403)
    return render_template("admin.html")


@app.route("/admin/reports", methods=["GET", "POST"])
def admin_reports():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if not session["user"]["admin"]:
        abort(403)
    if request.method == "POST":
        mysql.delete("reports", {"id": request.values["id"]})
        return redirect("/admin/reports")
    data = mysql.select("reports", ["id", "from", "atc_id", "time"],
                        order_by=["time"])
    reports = []
    for i in data:
        reports.append({
            "id": i[0],
            "from": users.get_by_id(i[1]),
            "article": articles.get(i[2]),
            "time": format_time(i[3])
        })
    return render_template("admin_reports.html", reports=reports)


@app.route("/admin/hidded-atc")
def admin_hiddedatc():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if not session["user"]["admin"]:
        abort(403)
    _data = mysql.run_code(
        "SELECT `id`, `title`, `from`, `hide` FROM articles WHERE `hide`>=1 ORDER BY `id` DESC LIMIT 200;"
    )
    data = []
    for i in _data:
        data.append({
            "id": i[0],
            "title": i[1],
            "from": users.get_by_id(i[2]),
            "hide": i[3]
        })
    return render_template("admin_hiddedatc.html", data=data)


@app.route("/admin/top-atc", methods=["POST"])
def admin_topatc():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if not session["user"]["admin"]:
        abort(403)
    try:
        atc_id = int(request.form["id"])
        mysql.update("articles", {"top": 1}, {"id": atc_id})
        flash("置顶成功！")
    except Exception as e:
        flash(f"置顶失败！\n<br />\n{e}")
    return redirect("/admin")


@app.route("/admin/untop-atc", methods=["POST"])
def admin_untopatc():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if not session["user"]["admin"]:
        abort(403)
    try:
        atc_id = int(request.form["id"])
        mysql.update("articles", {"top": 0}, {"id": atc_id})
        flash("取消置顶成功！")
    except Exception as e:
        flash(f"取消置顶失败！\n<br />\n{e}")
    return redirect("/admin")


@app.route("/admin/top-cmt", methods=["POST"])
def admin_topcmt():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if not session["user"]["admin"]:
        abort(403)
    try:
        atc_id = int(request.form["atc_id"])
        cmt_floor = int(request.form["cmt_floor"])
        cmt_id = mysql.select("comments", ["id"],
                              {"under": atc_id})[cmt_floor - 1][0]
        mysql.update("comments", {"top": 1}, {"id": cmt_id})
        flash("置顶成功！")
    except Exception as e:
        flash(f"置顶失败！\n<br />\n{e}")
    return redirect("/admin")


@app.route("/admin/untop-cmt", methods=["POST"])
def admin_untopcmt():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if not session["user"]["admin"]:
        abort(403)
    try:
        atc_id = int(request.form["atc_id"])
        cmt_floor = int(request.form["cmt_floor"])
        cmt_id = mysql.select("comments", ["id"],
                              {"under": atc_id})[cmt_floor - 1][0]
        mysql.update("comments", {"top": 0}, {"id": cmt_id})
        flash("取消置顶成功！")
    except Exception as e:
        flash(f"取消置顶失败！\n<br />\n{e}")
    return redirect("/admin")


@app.route("/admin/hide-atc", methods=["POST"])
def admin_hideatc():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if not session["user"]["admin"]:
        abort(403)
    try:
        atc_id = int(request.form["id"])
        level = int(request.form["level"])
        mysql.update("articles", {"hide": level}, {"id": atc_id})
        articles.reget(atc_id)
        articles.articles.pop(atc_id)
        flash("删除成功！")
    except Exception as e:
        flash(f"删除失败！\n<br />\n{e}")
    return redirect("/admin")


@app.route("/admin/del-atc", methods=["POST"])
def admin_delatc():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if not session["user"]["admin"]:
        abort(403)
    try:
        atc_id = int(request.form["id"])
        mysql.delete("articles", {"id": atc_id})
        articles.cnt -= 1
        articles.articles.pop(atc_id)
        flash("删除成功！")
    except Exception as e:
        flash(f"删除失败！\n<br />\n{e}")
    return redirect("/admin")


@app.route("/admin/del-cmt", methods=["POST"])
def admin_delcmt():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if not session["user"]["admin"]:
        abort(403)
    try:
        atc_id = int(request.form["atc_id"])
        cmt_floor = int(request.form["cmt_floor"])
        data = mysql.select("comments", ["id"], {"under": atc_id})
        mysql.delete("comments", {"id": data[cmt_floor - 1][0]})
        flash("删除成功！")
    except Exception as e:
        flash(f"删除失败！\n<br />\n{e}")
    return redirect("/admin")


@app.route("/sadmin")
def sadmin_index():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if session["user"]["admin"] != 2:
        abort(403)
    return render_template("sadmin.html")


@app.route("/sadmin/del-user", methods=["POST"])
def sadmin_deluser():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if session["user"]["admin"] != 2:
        abort(403)
    try:
        user_id = int(request.form["user_id"])
        mysql.update("users", {"password": "封号"}, {"id": user_id})
        users.blacklist.append(user_id)
        users.flush(user_id)
        flash("封禁成功！")
    except Exception as e:
        flash(f"封禁失败！\n<br />\n{e}")
    return redirect("/sadmin")


@app.route("/sadmin/add-admin", methods=["POST"])
def sadmin_addadmin():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if session["user"]["admin"] != 2:
        abort(403)
    try:
        user_id = int(request.form["user_id"])
        level = int(request.form["level"])
        mysql.update("users", {"admin": level}, {"id": user_id})
        users.flush(user_id)
        flash("操作成功！")
    except Exception as e:
        flash(f"操作失败！\n<br />\n{e}")
    return redirect("/sadmin")


@app.route("/sadmin/add-tag", methods=["POST"])
def sadmin_addtag():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if session["user"]["admin"] != 2:
        abort(403)
    try:
        user_id = int(request.form["user_id"])
        tags = request.form["tags"]
        mysql.update("users", {"tags": tags}, {"id": user_id})
        users.flush(user_id)
        flash("操作成功！")
    except Exception as e:
        flash(f"操作失败！\n<br />\n{e}")
    return redirect("/sadmin")


@app.route("/sadmin/rm-admin", methods=["POST"])
def sadmin_rmdamin():
    info_init()
    if not session.get("user"):
        return redirect("/user/login?from=" + request.url)
    if session["user"]["admin"] != 2:
        abort(403)
    try:
        user_id = int(request.form["user_id"])
        mysql.update("users", {"admin": 0}, {"id": user_id})
        users.flush(user_id)
        flash("操作成功！")
    except Exception as e:
        flash(f"操作失败！\n<br />\n{e}")
    return redirect("/sadmin")


@app.route("/test")
def test():
    return str(notices.get(1)) + "\n" + str(notices.notices) + "\n" + str(
        session["user"]["id"])


@app.route("/404")
@app.errorhandler(404)
def error_404(error):
    return render_template("404.html"), 404


@app.route("/410")
@app.errorhandler(410)
def error_410(error):
    return redirect("/user/logout")


@app.context_processor
def default():
    return {
        "user":
        session.get("user"),
        "title":
        "QA瓜田",
        "logined":
        bool(session.get("user")),
        "notice":
        session.get("user") and notices.get(session["user"]["id"])[::-1] or [],
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7399, debug=True)
