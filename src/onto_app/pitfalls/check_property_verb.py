import spacy
from re import finditer

def split_by_camel_case(identifier):
    # Split string by camel-case
    matches = finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    return " ".join([m.group(0) for m in matches])

nlp = spacy.load("en_core_web_sm")

def exists_verb(prop):
    prop = " ".join([split_by_camel_case(elem) for elem in prop.split("_")]).lower()
    VERBS = ["VERB", "ADV", "AUX"]
    verb_array = [tok for tok in nlp(prop) if tok.pos_ in VERBS]
    return True if verb_array else False

def scan(ontology):
    '''
    Checks if property labels have verbs in them.
    Args:
        Ontology: Parsed Ontology object
    Returns:
        List: List of pitfalls, which are 2-tuples of the form (<criticality>, <warning_message>)
    '''
    props = ontology.object_properties + ontology.data_properties

    pitfalls = []
    for prop in props:
        prop = ontology.extract_ID(prop)
        if not exists_verb(prop):
            warning_msg = "Property {} does not have any verbs in label. Invalid label?".format(prop)
            pitfalls.append(("Low", warning_msg))

    return pitfalls