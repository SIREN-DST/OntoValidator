import sys, math
import subprocess
from os import listdir
from os.path import isfile, join
import xml.dom.minidom
from ontology import *
import tweepy
from tweepy import OAuthHandler
import numpy as np
from tweepy import API
from tweepy import Cursor
from datetime import datetime, date, time, timedelta
from collections import Counter 
import tensorflow_hub as hub
import string
import sys
from scipy import spatial
from collections import defaultdict
from sqlalchemy import create_engine
name = sys.argv[1]

USE_link = "https://tfhub.dev/google/universal-sentence-encoder-large/5?tf-hub-format=compressed"
model = hub.load(USE_link)

NUM_STATUSES = 20 # Total number of user tweets to retreive
RELEVANT_PERCENTAGE = 0.25 # Percentage of most relevant tweets to average when calculating tweet credibility

MAX_FRIENDS = 5 # Total number of friends to search
RELEVANT_FRIENDS = 0.4 # Percentage of most relevant friends to average when calculating friend credibility

TWEETS_RELEVANCE = 1 # Coefficient of tweet cred while calculating overall credibility
FRIENDS_RELEVANCE = 0.5 # Coefficient of tweet cred while calculating overall credibility

def extractUSEEmbeddings(words):
    word_embeddings = model(words)
    return word_embeddings.numpy()

def cos_sim(a,b):
    # Returns cosine similarity of two vectors
    return 1 - spatial.distance.cosine(a, b)

def generateScore(text_array):
    all_embs = extractUSEEmbeddings(text_array + ["Pizza"])
    return [cos_sim(tweet_emb, all_embs[-1]) for tweet_emb in all_embs[:-1]]

access_token = "1192925360851013632-a1OH6gVyKWcmvMzeGkeQWNJYGGmQN9"
access_token_secret = "Kranny95fVLF5bn9pCrB4B2TXjM4oTnT9BX3vztxEPrDf"
consumer_key = "9NDG7eIVsrouj4CS2M7LoNjM1"
consumer_secret = "y1z075l563BwcL8XtI7GzQzEnvo1jEEzmcmR1NFBxhYPFokYzu"

auth = OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
auth_api = API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, retry_count=3, retry_delay=60)

account_list = []

def inOntology(node):
    input_ontology = "data/input/ontologies/" + name + ".owl"
    ont = Ontology(input_ontology)
    classes = [split_by_camel_case(elem).lower() for elem in ont.classes]
    instances = list(set(flatten([tuple([split_by_camel_case(elem).lower() for elem in instance]) for instance in ont.instances])))
    classes += instances
    node = split_by_camel_case(node.split("#")[-1]).lower() 
    return node in classes

def add_relation_with_credibility_only(scores_dict):
    engine = create_engine('sqlite:///onto.db', echo = True)
    c = engine.connect()
    trans = c.begin()
    
    query = """SELECT * FROM class_decisions INNER JOIN class_relations ON class_decisions.relation_id = class_relations.id """
    result = c.execute(query)
    
    full_results = list(result.fetchall())
    results_list = [(o['relation_id'],o['property'],o['domain'],o['range']) for o in full_results]
    
    relation_dict, nodes_dict = {}, {}

    for tup in results_list:
        for o in full_results:
            if(tup[1] == o['property'] and tup[2] == o['domain'] and tup[3] == o['range']):
                if tup in relation_dict:
                    if not math.isinf(relation_dict[tup][o['approved']]):
                        relation_dict[tup][o['approved']] += scores_dict[o['user_id']]
                    else:
                        relation_dict[tup][o['approved']] = scores_dict[o['user_id']]
                else:
                    if o['approved']:
                        relation_dict[tup] = [0, scores_dict[o['user_id']]]
                    else:
                        relation_dict[tup] = [scores_dict[o['user_id']], -math.inf]

    query = """SELECT * FROM node_decisions INNER JOIN nodes ON node_decisions.node_id = nodes.id """
    result = c.execute(query)
    
    full_results = list(result.fetchall())
    results_list = [(o['node_id'],o['name']) for o in full_results]
    

    for tup in results_list:
        for o in full_results:
            if(tup[0] == o['node_id'] and tup[1] == o['name']):
                if tup[1] in nodes_dict:
                    if not math.isinf(nodes_dict[tup[1]][o['approved']]):
                        nodes_dict[tup[1]][o['approved']] += scores_dict[o['user_id']]
                    else:
                        nodes_dict[tup[1]][o['approved']] = scores_dict[o['user_id']]
                else:
                    if o['approved']:
                        nodes_dict[tup[1]] = [0, scores_dict[o['user_id']]]
                    else:
                        nodes_dict[tup[1]] = [scores_dict[o['user_id']], -math.inf]

    relation_decisions, nodes_decisions = defaultdict(int), defaultdict(int)
    for tup in relation_dict:
        relation_decisions[tup] = int(np.argmax(relation_dict[tup]))
    for tup in nodes_dict:
        nodes_decisions[tup] = int(np.argmax(nodes_dict[tup]))

    for tup in relation_decisions:
        if relation_decisions[tup] and not ((nodes_decisions[tup[2]] or inOntology(tup[2])) and (nodes_decisions[tup[3]] or inOntology(tup[3]))):
            print ("Rejecting {}".format(tup))
            relation_decisions[tup] = 0

    insert_query = """INSERT INTO final_class_decisions (relation_id, approved)
                        VALUES (:relation_id, :approved)"""
    for tup in relation_decisions:
        args = {'relation_id': tup[0], 'approved': relation_decisions[tup]}
        c.execute(insert_query,args)

    insert_query = """INSERT INTO final_node_decisions (node_id, approved)
                    VALUES (:node_id, :approved)"""
    for tup in nodes_decisions:
        args = {'node_id': tup[0], 'approved': nodes_decisions[tup]}
        c.execute(insert_query,args)

    trans.commit()

def limit_handled(cursor):
    count=0
    while True:
        try:
            count+=1
            yield cursor.next()
        except tweepy.RateLimitError:
            print(count/2302*100)
            time.sleep(15 * 60)

def create_final_ontology(name):
    print ("Enriching {} with extracted relations".format(name))

    global baseurl
    if name == "pizza":
        baseurl = "https://serc.iiit.ac.in/downloads/ontology/pizza.owl"
    elif name == "security":
        baseurl = "https://serc.iiit.ac.in/downloads/ontology/securityontology.owl"

    input_ontology = "data/input/ontologies/" + name + ".owl"
    ont = Ontology(input_ontology)
    engine = create_engine('sqlite:///onto.db', echo = True)

    c = engine.connect()
    trans = c.begin()

    result = c.execute('''SELECT domain, range, property FROM class_relations 
        INNER JOIN final_class_decisions ON class_relations.id = final_class_decisions.relation_id
        INNER JOIN ontologies ON class_relations.onto_id = ontologies.id
        WHERE ontologies.name = :name AND final_class_decisions.approved = 1''', {'name': name})
    new_relations = list(result.fetchall())

    classes = [split_by_camel_case(elem).lower() for elem in ont.classes]
    instance_pairs = [tuple([split_by_camel_case(elem).lower() for elem in instance]) for instance in ont.instances]

    for (class_domain, class_range, relation) in new_relations:
        class_domain, class_range = class_domain.split("#")[-1], class_range.split("#")[-1]
        domain_iri, range_iri = str(class_domain), str(class_range)
        domain_label, range_label = split_by_camel_case(class_domain), split_by_camel_case(class_range)
        relation_iri = ''.join(x for x in relation.lower().title() if not x.isspace())

        if relation == "subclassOf":
            if domain_label.lower() in classes:
                ont.add_subclass_to_existing_class(baseurl, domain_label, range_iri, range_label)
            else:
                ont.create_class_with_subclass(baseurl, domain_iri, range_iri, domain_label, range_label)

        elif relation == "hasInstance":
            if (domain_label.lower(), range_label.lower()) not in instance_pairs:
                ont.create_instance(baseurl, domain_iri, range_iri, domain_label, range_label)

        else:
            print ("WARNING: Relation {} outside accepted categories: [hypernym, hyponym, concept, instance]".format(relation))
            if domain_label.lower() in classes:
                ont.add_property_to_existing_class(baseurl, domain_iri, relation_iri, domain_label, range_label)
            else:
                ont.create_class_with_property(baseurl, domain_iri, range_iri, relation_iri, domain_label, range_label)
    output_ontology = "data/final/" + name + ".owl"
    ont.write(output_ontology)

def calculate_twitter_credibility(user):
    tweets_data = auth_api.user_timeline(screen_name=user.screen_name, count=NUM_STATUSES, tweet_mode="extended")
    tweets = [tweet.full_text for tweet in tweets_data]
    tweet_scores = sorted(generateScore(tweets), reverse=True)
    relevant_tweet_scores = tweet_scores[:int(RELEVANT_PERCENTAGE * NUM_STATUSES)]
    tweets_cred = np.mean(relevant_tweet_scores)
    return tweets_cred

engine = create_engine('sqlite:///onto.db', echo = True)
    # conn = sqlite3.connect('onto.db')
    # c = conn.cursor()
c = engine.connect()
trans = c.begin()
query = """SELECT * FROM users"""
result = c.engine.execute(query)
for o in result.fetchall():
    account_list.append(o['username'])

account_list = list(set(account_list))
finalDict = defaultdict(int)

if len(account_list) > 0:
    for target in account_list:
        print("Calculating credibility for user {}".format(target))

        user = auth_api.get_user(target)
        tweets_cred = calculate_twitter_credibility(user)
        print("Tweet credibility of user {} is {}".format(target, tweets_cred))

        friend_creds = []
        for friend_id in Cursor(auth_api.friends_ids,screen_name=user.screen_name).items(MAX_FRIENDS):
            friend_user = auth_api.get_user(user_id=friend_id)
            friend_cred = calculate_twitter_credibility(friend_user)
            friend_creds.append(friend_cred)
        friend_creds = sorted(friend_creds, reverse=True)[:int(RELEVANT_FRIENDS * MAX_FRIENDS)]
        friends_cred = np.mean(friend_creds)
        print("Friend credibility of user {} is {}".format(target, friends_cred))
        
        finalDict[user.id] = TWEETS_RELEVANCE * tweets_cred + FRIENDS_RELEVANCE * friends_cred

add_relation_with_credibility_only(finalDict)

create_final_ontology(name)