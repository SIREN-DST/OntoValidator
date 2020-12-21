# Ontology Validator

Given a seed ontology and a list of concepts to be added to it, OntoValidator provides an easy-to-use interface for validation of the newly created ontology. Validation is crowdsourced, with [Twitter Credibility](TweetCredibility/) of the validator being used for quality control.

## Requirements:
- python3 and pip are prerequisites
- word2vec model trained on Twitter corpus downloaded from [here](https://drive.google.com/file/d/10B7cvx3xN7Ef_FxwIO8sigd1J1Ibe6Lu/view).

## Installation:
- Go to [src](src/) folder
- Run `pip3 install -r requirements.txt`. In case of any missing modules, please raise an issue.

## Initialization:
- Place the seed ontology (.owl file) in [src/onto_app/data/input](src/onto_app/data/input)
- Place the file containing new concepts and relations in [src/onto_app/data/input](src/onto_app/data/input) as .txt file
- Both the .owl file and .txt file should have same names. For instance, if your seed ontology is `pizza.owl`, name your text file as `pizza.txt`
- Edit path of word2vec model in [get_verified_ontology.py](src/onto_app/get_verified_ontology.py) based on the directory where it is downloaded.


## Validating the Ontology (Crowdsourced)
- Navigate to the [onto_app](src/onto_app) directory. 
- Run `export FLASK_APP=routes.py` and `export FLASK_ENV=development`
- Run `flask run` to start the server
- Login to the application using your Twitter account 
- Accept/reject concepts and relationships, as appropriate.
- Logout and stop the server.
- Multiple users validate the ontology this way through crowdsourcing

## Saving the decisions in final ontology (Developers only)
- Remove the files in [final](src/onto_app/data/final) if any.
- Run `python3 get_verified_ontology.py <file_name>`
- The decisions made by all the ontologists get evaluated based on their Twitter credibilities. 
- The decision with a higher score is chosen as the final decision, and written to the final ontology.
- Final ontology is stored in [src/data/final](src/onto_app/data/final) as `<file_name>.owl`
