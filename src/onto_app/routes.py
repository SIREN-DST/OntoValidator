from flask import Flask, request, redirect, url_for, session, g, flash, \
    render_template, jsonify
from onto_app import app, db
from pitfall_scanner import PitfallScanner
import os
from collections import Counter
from requests_oauthlib import OAuth1Session
from requests_oauthlib import OAuth1
from flask import send_file, send_from_directory, redirect, url_for, flash, current_app, session
from werkzeug.utils import secure_filename
import json
from onto_app.helper import *
import tweepy

# These config variables come from 'config.py'
client_key = "9NDG7eIVsrouj4CS2M7LoNjM1"
client_secret = 'y1z075l563BwcL8XtI7GzQzEnvo1jEEzmcmR1NFBxhYPFokYzu'
pitfalls_dict, final_data = {}, []
SECRET_KEY = 'AbYzXSaNdErS123@'
app.secret_key = SECRET_KEY
# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
db.init_app(app) 
# prevent cached responses
@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "-1"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

@app.route('/')
def home():
   return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    oauth = tweepy.OAuthHandler(client_key,client_secret)
    url = oauth.get_authorization_url()
    session['request_token'] = oauth.request_token
    return redirect(url)

@app.route('/authenticated')
def authenticated():
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    # state = session['state']
    print ("Inside authenticated")
    verification = request.args["oauth_verifier"]
    auth = tweepy.OAuthHandler(client_key, client_secret)
    try:
        auth.request_token = session["request_token"]
    except KeyError:
        flash("Please login again", "danger")
        return redirect('login')

    try:
        auth.get_access_token(verification)
    except tweepy.TweepError:
        flash("Failed to get access token", "danger")
        return redirect('login')

    session["access_token"] = auth.access_token
    session["access_token_secret"] = auth.access_token_secret
    tweepy_api = tweepy.API(auth)
    user_object = tweepy_api.me()
    userid = user_object.id
    session['credentials'] = credentials_to_dict(user_object)
    user_name = user_object.screen_name
    # print("Hello", userid, email)
    result = db.engine.execute("SELECT * FROM users WHERE id = :id", {'id': userid})
    if not result.fetchone():
        db.engine.execute("""INSERT INTO users (id, username, privilege) VALUES
                            (:id, :username, :privilege)""", {'id': userid, 'username': user_name, 'privilege': 0})
    session['userid'] = userid
    session['username'] = user_name

    return redirect(url_for('user'))

def credentials_to_dict(credentials):
  return {'id': credentials.id,
          'name': credentials.screen_name,
          }

@app.route("/pitfalls/<path:file>/", methods = ['GET'])
def pitfalls(file):
    if 'credentials' not in session:
        return redirect('login')
    if not pitfalls_dict or not pitfalls_dict.get(file, ""):
        return redirect('user')
    return render_template("pitfalls_summary.html", pitfalls=pitfalls_dict.get(file))

@app.route("/upload_ontology", methods = ['POST'])
def upload_ontology():
    if 'credentials' not in session or session["username"] != "remorax98":
        return redirect('login')
    global pitfalls_dict, final_data
    file = request.files["file"]
    if not file.filename:
        return jsonify([])
    ontology = os.path.abspath(os.path.join("data/input/ontologies/", file.filename))
    file.save(ontology)
    scanner = PitfallScanner(ontology, "pitfalls/")
    curr_pitfalls = scanner.scan()
    counts = {"High": 0, "Medium": 0, "Low": 0}
    counts.update(Counter([el[0] for el in curr_pitfalls]))
    ontology_name = '.'.join(ontology.split('/')[-1].split('.')[:-1])
    
    final_data.append((ontology_name, list(counts.values())))
    pitfalls_dict[ontology_name] = curr_pitfalls
    
    return render_template("admin_dashboard.html", ontologies=final_data, username=session['username'])

@app.route("/delete_ontology", methods = ['POST'])
def delete_ontology():
    if 'credentials' not in session or session["username"] != "remorax98":
        return redirect('login')

    print (request, request.json)
    ont_name = request.json['name']
    del pitfalls_dict[ont_name]
    print (pitfalls_dict.keys())

    final_data.remove([elem for elem in final_data if elem[0]==ont_name][0])
    try:
        os.remove(os.path.abspath(os.path.join("data/input/ontologies/", ont_name + ".owl")))
    except OSError:
        pass
    try:
        os.remove(os.path.abspath(os.path.join("data/input/files/", ont_name + ".tsv")))
    except OSError:
        pass

    return jsonify({"Message": "Deleted successfully!"})

@app.route('/user')
def user():
    if not 'credentials' in session:
        return redirect(url_for('home'))
    
    global pitfalls_dict, final_data
    ontologies = get_ontologies_on_server()
    
    if session["username"] != "remorax98":
        ontologies = ['.'.join(f.split('/')[-1].split('.')[:-1]) for f in ontologies]
        print ("Ontologies fetched from server: {}".format(ontologies))
        return render_template("user_dashboard.html", ontologies=ontologies, username=session['username'])

    if not pitfalls_dict or not final_data:
        for ontology in ontologies:
            scanner = PitfallScanner(ontology, "pitfalls/")
            curr_pitfalls = scanner.scan()
            counts = {"High": 0, "Medium": 0, "Low": 0}
            counts.update(Counter([el[0] for el in curr_pitfalls]))
            ontology_name = '.'.join(ontology.split('/')[-1].split('.')[:-1])
            final_data.append((ontology_name, list(counts.values())))
            pitfalls_dict[ontology_name] = curr_pitfalls

    return render_template("admin_dashboard.html", ontologies=final_data, username=session['username'])

@app.route('/download')
def download():
    if not 'credentials' in session:
        return redirect(url_for('home'))
    
    if session["username"] != "remorax98":
        return redirect(url_for('user'))

    return send_from_directory(directory=os.path.abspath("."), filename="onto.db")

@app.route('/logout')
def logout():
    if 'credentials' in session:
        del session['credentials']
        del session['username']
        del session['userid']
    return redirect(url_for('home'))

""" Stores decisions taken in frontend corresponding to relationships accept/reject into database """
@app.route('/decision', methods=["POST"])
def decision() :
    if request.method == 'POST' :
        """ Decisions stored """
        """ Index numbers used to extract specific content from already existing inner html. This will hold through across cases."""
        data = eval(str(request.data.decode("utf-8")))
        # if flag is 1, then relation, else node
        user_id = session['userid']
        onto_id = session['ontology']
        print (data)
        if data["flag"]:
            #when a relationship is accepted/rejected
            Prop = data["name"]
            Type = data["type"]
            Decision  = data["decision"]
            Domain = data["domain"]
            Range = data["range"]

            print("Relation Name: ", Prop)
            print("Domain: ", Domain)
            print("Range: ", Range)
            print("Decision: ", Decision)
            print("Type: ", Type)

            add_relation_decision(user_id, Prop, Domain, Range, Type, onto_id, {'Accept': 1, 'Reject':0}[Decision])

        else:
            # When a node is accepted or rejected.
            name = data["name"]
            Decision = data["decision"]

            print("Class: ", name)
            print("Decision:", Decision)

            """ Call add_decision on node from onto.py to store decision """
            add_node_decision(user_id, name, onto_id, {'Accept': 1, 'Reject':0}[Decision])

    return render_template("index.html")


""" Serve file and new relationships from backend corresponding to the filename given in the URL """
@app.route("/loadOntology/<path:file>/", methods = ['GET'])
def loadOntology(file) :
    """ Serve files and new relations from the backend """
    """ Ontologies ready to be rendered saved in data/json """

    if 'credentials' not in session:
        return redirect('login')

    json_file = file + '.json'
    uploads = os.path.join(current_app.root_path,"data/server-files/json")
    uploads = uploads + "/" + str(json_file)
    ontology_file = file + ".owl"
    enriched_file = file + ".tsv"

    result = db.engine.execute("SELECT id FROM ontologies WHERE name = :name", {'name': file})
    onto_id = result.fetchone()['id']
    session['ontology'] = onto_id

    result = db.engine.execute("""SELECT * FROM class_relations WHERE onto_id == :onto_id""",
        {'onto_id': str(onto_id)})
    new_relations = [(r['domain'], r['property'], r['range']) for r in result.fetchall()]
    print("New relations extracted for {} ontology are {}".format(file, new_relations))
    
    result = db.engine.execute("""SELECT * FROM nodes WHERE onto_id == :onto_id""",
        {'onto_id': str(onto_id)})
    new_nodes = [n['name'] for n in result.fetchall()]
    print("New nodes extracted for {} ontology are {}".format(file, new_nodes))
   
    with open(uploads,"r") as json_data:
        contents = json.load(json_data)
    # new_relations = list(set(new_relations))
    return render_template("index.html", OntologyContentJson=contents, 
        userId=session['userid'], 
        hiddenJSONRel=new_relations, 
        hiddenJSONNode=new_nodes, 
        emptyList=[])
