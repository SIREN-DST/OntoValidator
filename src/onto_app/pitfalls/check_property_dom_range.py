def scan(ontology):
    '''
    Checks if:
    1. Properties have domains and ranges
    2. If they do, whether these domains and ranges have labels/IDs
    3. If they do, whether these domains and ranges exist as classes in the ontology.
    Args:
        Ontology: Parsed Ontology object
    Returns:
        List: List of pitfalls, which are 2-tuples of the form (<criticality>, <warning_message>)
    '''
    props = ontology.object_properties + ontology.data_properties
    classes = ontology.classes

    pitfalls = []
    for prop in props:
        domain_children = ontology.get_child_node(prop, "rdfs:domain")
        range_children = ontology.get_child_node(prop, "rdfs:range")
        if not domain_children:
            warning_msg = "Property {} does not have a domain.".format(ontology.extract_ID(prop))
            pitfalls.append(("High", warning_msg))
        if not range_children:
            warning_msg = "Property {} does not have a range.".format(ontology.extract_ID(prop))
            pitfalls.append(("High", warning_msg))
        if not domain_children or not range_children:
            continue

        domain_prop = ontology.filter_null([ontology.extract_ID(el) for el in domain_children])
        range_prop = ontology.filter_null([ontology.extract_ID(el) for el in range_children])
        if not domain_prop:
            domain_prop = ontology.filter_null([ontology.extract_ID(el) for el in domain_children[0].getElementsByTagName("owl:Class")])
        if not range_prop:
            range_prop = ontology.filter_null([ontology.extract_ID(el) for el in range_children[0].getElementsByTagName("owl:Class")])
        
        if domain_prop and range_prop:
            faulty_domains = [domain for domain in domain_prop if domain not in classes]
            faulty_ranges = [Range for Range in range_prop if Range not in classes]
            if faulty_domains:
                warning_msg = "Domains {} of property {} do not exist as classes in ontology".format(", ".join(faulty_domains), ontology.extract_ID(prop))
                pitfalls.append(("Low", warning_msg))
            if faulty_ranges:
                warning_msg = "Ranges {} of property {} do not exist as classes in ontology".format(", ".join(faulty_ranges), ontology.extract_ID(prop))
                pitfalls.append(("Low", warning_msg))
            
        elif not domain_prop and range_prop:
            warning_msg = "Domain of property {} does not have label/ID".format(ontology.extract_ID(prop))
            pitfalls.append(("Medium", warning_msg))
        elif domain_prop and not range_prop:
            warning_msg = "Range of property {} does not have label/ID".format(ontology.extract_ID(prop))
            pitfalls.append(("Medium", warning_msg))
        else:
            warning_msg = "Both range/domain of property {} do not have label/ID".format(ontology.extract_ID(prop))
            pitfalls.append(("Medium", warning_msg))

    return pitfalls