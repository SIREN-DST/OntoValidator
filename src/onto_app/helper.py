import subprocess
from os import listdir
from os.path import isfile, join, abspath
import glob
from ontology import *
from onto_app import db
from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS
from collections import defaultdict

OWL2VOWL = 'OWL2VOWL-0.3.5-shaded.jar'
baseurl = "https://serc.iiit.ac.in/downloads/ontology/test.owl"

def is_blank(node):
    if not '#' in node:
        return True
    else:
        return False

def create_validatable_ontology(input_ontology, output_ontology, url, new_relations):
    print ("Enriching {} with extracted relations".format(output_ontology))

    ont = Ontology(input_ontology)
    classes = [split_by_camel_case(elem).lower() for elem in ont.classes]

    for (term1,term2,relation) in new_relations:
        term1, term2 = term1.split("#")[-1], term2.split("#")[-1]
        iri1, iri2 = str(term1), str(term2)
        term1, term2 = split_by_camel_case(term1), split_by_camel_case(term2)
        relation_iri = ''.join(x for x in relation.lower().title() if not x.isspace())

        if relation.lower().strip() in ["hypernym", "hyponym"]:
            if relation.lower().strip() == "hyponym":
                class_iri = iri2
                class_label = term2
                subclass_iri = iri1
                subclass_label = term1
            else:
                class_iri = iri1
                class_label = term1
                subclass_iri = iri2
                subclass_label = term2

            if class_label.lower() in classes:
                ont.add_subclass_to_existing_class(url, class_label, subclass_iri, subclass_label)
            else:
                ont.create_class_with_subclass(url, class_iri, subclass_iri, class_label, subclass_label)

        elif relation.lower().strip() in ["instance", "concept"]:
            relation_iri = "hasInstance"
            if relation.lower().strip() == "instance":
                instance_iri = iri2
                instance_label = term2
                concept_iri = iri1
                concept_label = term1
            else:
                instance_iri = iri1
                instance_label = term1
                concept_iri = iri2
                concept_label = term2

            if concept_label.lower() in classes:
                ont.add_property_to_existing_class(url, instance_iri, relation_iri, concept_label, instance_label)
            else:
                ont.create_class_with_property(url, concept_iri, instance_iri, relation_iri, concept_label, instance_label)

        else:
            print ("WARNING: Relation {} outside accepted categories: [hypernym, hyponym, concept, instance]".format(relation))
            if term2.lower() in classes:
                ont.add_property_to_existing_class(url, iri1, relation_iri, term2, term1)
            else:
                ont.create_class_with_property(url, iri2, iri1, relation_iri, term2, term1)

    ont.write(output_ontology)

def createParsedRelations(file, fname):
    allParsedRelations = []
    for line in open(file, "r").readlines():
        if line.split("\t"):
            (term1, term2, relation) = line.split("\t")
            iri1 = ''.join(x for x in term1.lower().title() if not x.isspace())
            iri2 = ''.join(x for x in term2.lower().title() if not x.isspace())
            concept1 = baseurl + "#" + iri1
            concept2 = baseurl + "#" + iri2
            allParsedRelations.append(" ".join([concept1, concept2, relation]))
    string = "\n".join(allParsedRelations)
    open("./data/server-files/files/" + str(fname) + '.tsv', "w+").write(string)
    return


def add_onto_file(admin_id, name):
    # compile OWL to JSON using OWL2VOWL
    global baseurl
    if name=="pizza":
        baseurl = "https://serc.iiit.ac.in/downloads/ontology/pizza.owl"
    elif name=="security":
        baseurl = "https://serc.iiit.ac.in/downloads/ontology/securityontology.owl"
    json_path = './data/server-files/json/' + str(name) + '.json'
    raw_extracted_relations = './data/input/files/' + str(name) + '.tsv'
    ontology_path = './data/input/ontologies/' + str(name) + '.owl'
    f = open(json_path, 'w+')
    allTriples = [el.strip().split("\t")[:3] for el in open(raw_extracted_relations).read().split("\n") if el]
    print ("Relations to enrich: {}".format(allTriples))

    new_relations, new_nodes = get_new_relations(ontology_path, raw_extracted_relations)

    outputfile = "./data/server-files/ontologies/" +str(name) + '.owl'
    create_validatable_ontology(ontology_path, outputfile, baseurl, new_relations)
    print ("Enriched {} ontology created...".format(name))

    try:
        subprocess.run(['java', '-jar', OWL2VOWL, '-file', outputfile, '-echo'], stdout=f)
    except:
        raise RuntimeError

    # Create record for ontology in database
    insert_query = """INSERT INTO ontologies (name, admin_id)
                        VALUES (:name, :admin_id)"""
    result = db.engine.execute(insert_query, {'name': str(name), 'admin_id': admin_id})#'filepath': filepath, )
    new_ontology_id = result.lastrowid
    db.session.commit()
    # add new relations to database
    
    add_relations_to_db(new_relations, new_ontology_id)
    add_nodes_to_db(new_nodes, new_ontology_id)
    print ("Written new relations and nodes to db for {}".format(name))
    # add_subclasses_to_db(new_subclasses, new_ontology_id)

def add_new_ontologies():
    ontologies = ['.'.join(f.split('.')[:-1]) for f in listdir("./data/input/ontologies/") if isfile(join("./data/input/ontologies/", f)) and f.endswith(".owl")]
    ontologies = [ont for ont in ontologies if ont]
    result = db.engine.execute("""SELECT name FROM ontologies""")
    db_ontologies = [o['name'] for o in result.fetchall()]
    for onto in ontologies:
        if onto not in db_ontologies:
            print ("Adding {}".format(onto))
            add_onto_file(0, onto)

def get_new_relations(ontology_path, relations_file):
    ont = Ontology(ontology_path)
    
    classes = [split_by_camel_case(elem).lower() for elem in ont.classes]
    subclasses = [tuple([split_by_camel_case(elem).lower() for elem in subclass]) for subclass in ont.subclasses]
    instances = [tuple([split_by_camel_case(elem).lower() for elem in instance]) for instance in ont.instances]
    
    final_relations, final_nodes = [], []

    for line in open(relations_file, "r").read().split("\n"):
        if line.split("\t"):
            (term1, term2, relation) = line.split("\t")
            
            if relation in ["hyponym", "hypernym"]:
                if relation == "hyponym":
                    tup = (term1.lower(), term2.lower())
                else:
                    tup = (term2.lower(), term1.lower())
                if tup not in subclasses:
                    final_relations.append((term1, term2, relation))
            
            elif relation in ["concept", "instance"]:
                if relation == "instance":
                    tup = (term1.lower(), term2.lower())
                else:
                    tup = (term2.lower(), term1.lower())
                if tup not in instances:
                    final_relations.append((term1, term2, relation))

            else:
                final_relations.append((term1, term2, relation))

        if term1.lower() not in classes:
            final_nodes.append(term1)
        if term2.lower() not in classes:
            final_nodes.append(term2)

    final_relations, final_nodes = list(set(final_relations)), list(set(final_nodes))
    parsed_relations, parsed_nodes = [], []

    for (term1, term2, relation) in final_relations:
        iri1 = ''.join(x for x in term1.lower().title() if not x.isspace())
        iri2 = ''.join(x for x in term2.lower().title() if not x.isspace())
        concept1 = baseurl + "#" + iri1
        concept2 = baseurl + "#" + iri2
        parsed_relations.append((concept1, concept2, relation))

    for term in final_nodes:
        iri = ''.join(x for x in term.lower().title() if not x.isspace())
        concept = baseurl + "#" + iri
        parsed_nodes.append((concept))

    return parsed_relations, parsed_nodes

def add_nodes_to_db(nodes, onto_id):
    insert_query = """INSERT INTO
                    nodes (name, onto_id)
                    VALUES (:name, :onto_id)"""
    args = {'name': None, 'onto_id': onto_id}
    for n in nodes:
        args['name'] = n
        result = db.engine.execute(insert_query, args)
        # print(result)
    db.session.commit()

def add_relations_to_db(relations, onto_id):
    insert_query = """INSERT INTO
                    class_relations (domain, property, range, onto_id)
                    VALUES (:domain, :property, :range, :onto_id)"""
    for r in relations:
        relation, class_domain, class_range = r[2], r[1], r[0]
        if r[2] in ["hypernym", "hyponym"]:
            relation = "subclassOf"
            if r[2] == "hypernym":
                class_domain = r[0]
                class_range = r[1]
            else:
                class_domain = r[1]
                class_range = r[0]
        elif r[2] in ["concept", "instance"]:
            relation = "hasInstance"
            if r[2] == "instance":
                class_domain = r[0]
                class_range = r[1]
            else:
                class_domain = r[1]
                class_range = r[0]
        
        args = {}
        args['domain'] = class_domain
        args['range'] = class_range
        args['property'] = relation
        args['onto_id'] = onto_id
        result = db.engine.execute(insert_query, args)
    db.session.commit()

def add_relation_with_credibility_only(twitter_users):
    # query = """SELECT * FROM class_decisions"""
    # result = db.engine.execute(query)
    query = """SELECT * FROM class_decisions INNER JOIN class_relations ON class_decisions.relation_id =class_relations.id where class_decisions.id= ?"""
    result = db.engine.execute(query)
    relation_list = [(o['relation_id'],o['property'],o['domain'],o['range']) for o in result.fetchall()]
    relation_set = set(relation_list)
    relation_dict = defaultdict(int)
    relation_count = defaultdict(int)
    query = """SELECT * FROM class_decisions INNER JOIN class_relations ON class_decisions.relation_id =class_relations.id where class_decisions.id= ?"""
    result = db.engine.execute(query)
    for tup in relation_set :
        for o in result.fetchall():
            if(tup[0] == o['property'] and tup[1] == o['domain'] and tup[2] == o['range']):
                relation_dict[tup]+=(o['approved']*twitter_users[o['user_id']])
                relation_count[tup]+=twitter_users[o['user_id']]
            else:
                pass


    query = """DELETE * FROM class_decisions WHERE class_decisions.id = ?"""
    result = db.engine.execute(query)
    for tup,score in relation_dict.items():
        score = score/relation_count[tup]
        relation_dict[tup] = score
    for tup,score in relation_dict.items():
        if score > 0.5:
            args = {
                    'relation_id': tup[0],
                        # 'property': property,
                    'approved': 1,
                    'user_id': None
                    }
            insert_query = """INSERT INTO class_decisions
                        (relation_id, user_id, approved)
                        VALUES (:relation_id, :user_id, :approved)"""
            db.engine.execute(insert_query,args)
        else:
            args = {
                    'relation_id': tup[0],
                        # 'property': property,
                    'approved': 0,
                    'user_id': None
                    }
            insert_query = """INSERT INTO class_decisions
                        (relation_id, user_id, approved)
                        VALUES (:relation_id, :user_id, :approved)"""
            db.engine.execute(insert_query,args)








def add_relation_decision(user_id, relation, class_domain, class_range, relation_type, onto_id, decision):
    relation = ''.join(relation.split("#")[-1].split(" "))
    args = {
        'onto_id': onto_id,
        'property': relation,
        'domain': class_domain,
        'range': class_range
        # 'quantifier': quantifier
    }
    
    print("user_id:", user_id)
    print("relation:", relation)
    print("domain:", class_domain)
    print("range:", class_range)
    print("onto_id:", onto_id)
    print("decision:", decision)

    select_relation_query = """SELECT id FROM class_relations
                            WHERE onto_id = :onto_id
                            AND UPPER(property) = UPPER(:property)
                            AND UPPER(domain) = UPPER(:domain)
                            AND UPPER(range) = UPPER(:range)"""

    result = db.engine.execute(select_relation_query, args)

    relation_id = result.fetchone()['id']
    
    result = db.engine.execute("""SELECT * FROM class_decisions 
            WHERE user_id = :user_id AND relation_id = :relation_id""", {'user_id': user_id, 'relation_id': relation_id})

    if result.fetchone():
        db.engine.execute("""UPDATE class_decisions SET approved = :decision
        WHERE user_id = :user_id AND relation_id = :relation_id""", 
        {'user_id': user_id, 'relation_id': relation_id, 'approved': decision})
    else:
        insert_query = """INSERT INTO class_decisions
                        (relation_id, user_id, approved)
                        VALUES (:relation_id, :user_id, :approved)"""
        result = db.engine.execute(insert_query, {
            'relation_id': relation_id,
            'user_id': user_id,
            'approved': decision
        })


def add_node_decision(user_id, name, onto_id, decision):
    relation_query = """SELECT id FROM nodes
                        WHERE onto_id = :onto_id
                            AND name = :name"""

    result = db.engine.execute(relation_query, {
        'onto_id': onto_id,
        'name': name,
    })
    print(user_id)
    print(onto_id)
    print(decision)
    print(name)
    node_id = result.fetchone()['id']

    result = db.engine.execute("""SELECT * FROM node_decisions 
            WHERE user_id = :user_id AND node_id = :node_id""", {'user_id': user_id, 'node_id': node_id})
    
    if result.fetchone():
        db.engine.execute("""UPDATE node_decisions SET approved = :decision
        WHERE user_id = :user_id AND node_id = :node_id""", 
        {'user_id': user_id, 'node_id': node_id, 'approved': decision})
    else:
        insert_query = """INSERT INTO node_decisions
                            (node_id, user_id, approved)
                            VALUES (:node_id, :user_id, :approved)"""
        result = db.engine.execute(insert_query, {
            'node_id': node_id,
            'user_id': user_id,
            'approved': decision
        })

def get_ontologies_on_server():
    ontologies = [abspath(f) for f in glob.glob("./data/input/ontologies/*") if isfile(f) and f.endswith(".owl")]
    return ontologies
