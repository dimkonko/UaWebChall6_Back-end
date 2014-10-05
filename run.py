import os
import json
from urlparse import urlparse, parse_qs

import requests
from flask import Flask, redirect, request, render_template, session

PORT = 5000
APP_ID = "cf117f358f5e6161acfa972c7ed17a3c"
REDIRECT_URL = "http://localhost:5000/auth"

app = Flask(__name__)
app.secret_key = os.urandom(27)
app.debug = True

auth_url = "https://api.worldoftanks.ru/wot/auth/login/?" +\
		   "application_id={0}&redirect_uri={1}".format(
		   			APP_ID, REDIRECT_URL)

user_data = dict()
neighbors_req = None

@app.route("/")
def index():
	return redirect(auth_url)

@app.route("/auth")
def auth():
	# req_data = request.url.split("?")[0].split("&").split("=")

	req_data = parse_qs(urlparse(request.url).query)
	if req_data["status"] != ["ok"]:
		print "Auth failed"
		return redirect("/error")
	
	del req_data["status"]
	del req_data["expires_at"]

	for key, val in req_data.iteritems():
		user_data[key] = val[0]

	print "User data"
	print user_data

	session["nickname"] = user_data["nickname"]

	return redirect("/neighbors")

@app.route("/main")
def main():
	if "nickname" not in session:
		return "User is not logged in."
	return render_template("main.html", nickname=user_data["nickname"])


@app.route("/neighbors")
def neighbors():
	if "nickname" not in session:
		return "User is not logged in."
	error_msg = ""

	global neighbors_req
	neighbors_req = None
	neighbors_req = get_req_data("ratings/neighbors/",
			"type=28&account_id={0}&rank_field=frags_count&limit=20".format(user_data["account_id"]),
			"frags_count,battles_count.value,account_id")

	if not neighbors_req:
		user_data["account_id"] = "5365"
		neighbors_req = get_req_data("ratings/neighbors/",
			"type=28&account_id={0}&rank_field=frags_count&limit=20".format(user_data["account_id"]),
			"frags_count,battles_count.value,account_id")

		error_msg = "You not in ranked list. Example will be shown for user with id '5365'"
	return render_template("neighbors.html", neighbors=neighbors_req, error_msg=error_msg)


@app.route("/tanks")
def tanks():
	if "nickname" not in session or not neighbors:
		return "User is not logged in."

	account_ids = ""
	print neighbors
	for field in neighbors_req:
		account_ids += str(field["account_id"]) + ","

	print "All battles"
	all_battles = get_req_data("ratings/accounts/",
			"type=all&account_id={0}".format(account_ids),
			"battles_count.value,account_id")
	if not all_battles:
		return redirect("/error")

	print "Tank ids req"
	all_tanks_req = get_req_data("encyclopedia/tanks/",
			fields_arg="name_i18n")
	if not all_tanks_req:
		return redirect("/error")

	print "User tanks: "
	user_stats_req = get_req_data("account/tanks/",
			"account_id={0}".format(account_ids),
			"tank_id,statistics.battles")
	if not user_stats_req:
		return redirect("/error")

	lines = list()
	line = list()
	for counter, tank_id in enumerate(all_tanks_req):
		line = [counter, tank_id]

		for acc_id in user_stats_req:
			battles_count = all_battles[acc_id]["battles_count"]["value"]
			cur_proc = 0
			for field in user_stats_req[acc_id]:
				if int(field["tank_id"]) == int(tank_id):
					cur_proc = calc_batle_proc(battles_count, 
							field["statistics"]["battles"])
			line.append(cur_proc)
		lines.append(line)
	return render_template("tanks.html", data=user_data, users_stats=lines)


@app.route("/error")
def error():
	return "Something went wrong :("


def get_req_data(url_body, url_args="", fields_arg=None):
	url = "https://api.worldoftanks.ru/wot/" + url_body + "?" + "application_id={0}&{1}".format(APP_ID,
			url_args)
	if fields_arg:
		print "ok"
		url += "&fields={0}".format(fields_arg)
	print "Url: ", url

	r = requests.get(url)
	req = json.loads(r.text)

	if "error" in req:
		print "Error: ", req["error"]
		return None

	return req["data"]

def calc_batle_proc(batles_count, battles_on_tank):
	return (int(battles_on_tank) * 100) / int(batles_count)

def create_line(line_id, tank_id, tank_name, user_stats_req):
	
	return line

if __name__ == "__main__":
	port = int(os.environ.get("PORT", 5000))
	app.run(host="0.0.0.0", port=port)
