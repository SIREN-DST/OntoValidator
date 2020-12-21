import spacy
from re import finditer

def split_by_camel_case(identifier):
    # Split string by camel-case
    matches = finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    return " ".join([m.group(0) for m in matches])

nlp = spacy.load("en_core_web_sm")

def is_proper_noun(instance):
    instance = " ".join([split_by_camel_case(elem) for elem in instance.split("_")]).lower()
    proper_noun = [tok for tok in nlp(instance) if tok.pos_ == "PROPN"]
    return True if proper_noun else False

def scan(ontology):
    '''
    Checks if instance labels have proper nouns in them.
    Args:
        Ontology: Parsed Ontology object
    Returns:
        List: List of pitfalls, which are 2-tuples of the form (<criticality>, <warning_message>)
    '''
    instances = [el[-1] for el in ontology.instances]

    pitfalls = []
    for instance in instances:
        if not is_proper_noun(instance):
            warning_msg = "Instance {} does not have any proper nouns in label. Invalid label?".format(instance)
            pitfalls.append(("Low", warning_msg))
    return pitfalls