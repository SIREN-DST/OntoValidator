def scan(ontology):
	'''
	Checks if instances have types and if they do, whether they exist as classes in the ontology.
	Args:
	    Ontology: Parsed Ontology object
	Returns:
	    List: List of pitfalls, which are 2-tuples of the form (<criticality>, <warning_message>)
	'''
	instances = ontology.root.getElementsByTagName("owl:NamedIndividual") + ontology.root.getElementsByTagName("owl:Thing")
	classes = ontology.classes
	pitfalls = []
	for instance in instances:
		types = ontology.get_child_node(instance, "rdf:type")
		if not types:
			warning_msg = "Instance {} does not have a type.".format(ontology.extract_ID(instance))
			pitfalls.append(("High", warning_msg))
			continue

		search_type = [instance_type for instance_type in types if ontology.extract_ID(instance_type) in classes]
		if not search_type:
			warning_msg = "Instance {} does not have types existing as classes in the ontology.".format(ontology.extract_ID(instance))
			pitfalls.append(("Medium", warning_msg))
	return pitfalls
