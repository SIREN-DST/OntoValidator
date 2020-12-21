from ontology import *
from glob import glob
import os
import pitfalls.__init__

def sort_compare(key):
	importance_dict = {"High": 3, "Medium": 2, "Low": 1 }
	return importance_dict[key[0]]

class PitfallScanner():
	"""docstring for PitfallScanner"""
	def __init__(self, ontology_path, pitfalls_dir):
		self.ontology = Ontology(ontology_path)
		self.pitfalls_dir = os.path.abspath(pitfalls_dir)	

	def scan(self):
		results = []
		for pitfall_module in pitfalls.__init__.__load_all__():
			results.extend(pitfall_module.scan(self.ontology))
		results.sort(key=sort_compare, reverse=True)
		return results