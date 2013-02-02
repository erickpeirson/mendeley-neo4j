
from pprint import pprint
from mendeley_client import *
import os
import sys
import urllib2
import xml.etree.ElementTree as ET
from py2neo import neo4j, cypher
import unicodedata

##########################################################
# All-purpose scripts for searching lists of objects
# e.g. contains(self.library,lambda x: x.name == "bob")
def ol_contains(list, filter):
    for x in list:
        if filter(x):
            return True
    return False
    
def ol_get(list, filter):
    for x in list:
        if filter(x):
            return x
    return False
##########################################################    
    
    
def normalize_text(string):
    return unicodedata.normalize('NFKD', string).encode('ascii', 'ignore')

##########################################################
def get_mendeley_documents ():
    mendeley_uri_prefix = "http://open.mendeley.com/library/document/"
    
    documents = []                                              # We'll put the document objects in here
    mendeley = create_client()
    doc_list = mendeley.folder_documents('40139031',items=57)   # List the contents of the Mendeley folder
    
    for entry in doc_list['document_ids']:                     # Now we need the detailed record for each document
        document = mendeley.document_details(entry)
        document = {    'uri' : mendeley_uri_prefix + document['id'],
                        'title' : document['title'],
                        'authors' : document['authors'],
                        'year' : document['year']           }
        documents.append(document)
    
    
    return documents

def get_node (uri):
    graph_db = neo4j.GraphDatabaseService("http://localhost:7474/db/data/")
    query = "START a=node(*) WHERE a.uri = '"+uri+"' RETURN a"
    data, metadata = cypher.execute(graph_db, query)
    if data:
        return data
    return None
    
    
def create_node (data):
    graph_db = neo4j.GraphDatabaseService("http://localhost:7474/db/data/")
    if data['type'] is 'Person':
        query = "create n = {title: '"+data['title']+"', uri: '"+data['uri']+"', type: 'Person'} return n"
    if data['type'] is 'Paper':
        query = "create n = {title: '"+data['title']+"', uri: '"+data['uri']+"', type: 'Paper', year: '"+data['year']+"'} return n"        
    data, metadata = cypher.execute(graph_db, query)
    return data

##########################################################
 
class ConceptPower:
    # Wrapper for ConceptPower API; returns an ElementTree root object
    def __init__ (self):
        self.server = "http://digitalhps-develop.asu.edu:8080/conceptpower/rest/"
    
        # Test it!
        response = urllib2.urlopen(self.server+"ConceptLookup/Bradshaw/Noun").read()
        root = ET.fromstring(response)
        if not len(root) > 0:
            print "Error! Could not connect to ConceptPower API"
            
    def search (self, query):
        response = urllib2.urlopen(self.server+"ConceptLookup/"+query+"/Noun").read()
        root = ET.fromstring(response)
        if len(root) > 0:
            return root
        return None
        
    def get (self, uri):
        response = urllib2.urlopen(self.server+"Concept?id="+uri).read()
        root = ET.fromstring(response)
        if len(root) > 0:
            return root
        return None
    
 ##########################################################       
    
class ConceptMapper:
    def __init__ (self):
        self.map = []
        return None
    
    # concept is a URI, and pattern can be anything (e.g. a name)
    def add (self, concept, pattern):
        if concept and pattern:
            self.map.append({'concept': concept, 'pattern': pattern})
            return True
        return None
        
    # Is the pattern already in the map? If so, return the URI.
    def check (self, pattern):
        found = ol_get(self.map, lambda x: x['pattern'] == pattern)
        if found:
            return found['concept']
        return None
    
    # So that we can use the map later
    def export (self, file):
        if file:
            f = open(file, "w")
            for entry in self.map:
                f.write(entry['concept'] + "\t" + entry['pattern'] + "\n")
            return True
        return None
        
    # Load a previously exported()ed map
    def load (self, file):
        if file:
            f = open(file, "r")
            for line in f:
                self.add (line.split("\t")[0], line.split("\t")[1])

# options must have id, title
def get_selection (options, prompt):
    found = False
    while not found:
        print prompt            #print "Possible matches found in ConceptPower: "        # Here are your options, user...
        for opt in options:
            print str(opt['id']) + " : " + opt['title']
        choice = raw_input("Please make a selection: ")         # Ask user for selection...

        selected = ol_get(options, lambda x: x['id'] == int(choice))
        
        if selected:                                   
            found = True
            return selected['id']
        else:
            print "Invalid selection. Please try again."      # Dipshit


 
#print get_selection ( [
#                    {'id': 0,   'title': 'Bob'},
#                    {'id': 1,   'title': 'Igor'} ],
#                        "Please choose one!" )

cp = ConceptPower()
map = ConceptMapper()


papers = get_mendeley_documents()

for paper in papers:
    
    node = get_node (paper['uri'])                              # Paper node exists?
    print paper['title'] + "\n"

    if node is None:                                                # If it doesn't exist, create a new one!
        #print "Create node: "
        #print ({'uri': normalize_text(paper['uri']), 'title': normalize_text(paper['title']), 'year': normalize_text(paper['year']), 'type': 'Paper'})
        create_node ({'uri': normalize_text(paper['uri']), 'title': normalize_text(paper['title']), 'year': normalize_text(paper['year']), 'type': 'Paper'})
        node = get_node (paper['uri'])
        
    authors = paper['authors']

    for author in authors:
        # First, find the right concept in ConceptPower. Won't proceed without a ConceptPower URI.
        uri_in_map = map.check (author['surname'] + ", " + author['forename'])  # Check the mapper first
        if uri_in_map:                                                          # Already mapped it?
            concept_uri = uri_in_map                                            # Yes. That was easy!
        else:
            print "*** Concept needed for Mendeley author: " + author['surname'] + ", " + author['forename'] + " ***\n"
            
            need_new_concept = False
            cp_candidates = cp.search ( author['surname'] )                     # Search ConceptPower by last name only
            if cp_candidates is None:
                need_new_concept = True
            else:                                      # Did it find anything? Yes.
                i = 0
                options = []
                
                for candidate in cp_candidates:
                    if candidate.tag == "{http://www.digitalhps.org/}conceptEntry":
                        options.append({'id': i, 'title': candidate[1].text, 'uri': candidate[0].text})
                        i += 1
                options.append({'id': i, 'title': '--None of these--'})   
                

                user_selection = get_selection (options, "Potential matches found in ConceptPower. Please make a selection:\n")
                selected = ol_get (options, lambda x: x['id'] == user_selection)
                if selected == '--None of these--':
                    need_new_concept = True
                else:
                    concept_uri = selected ['uri']                              # Using the ConceptPower URI selected from the list
                    author_title = selected ['title']
                    map.add ( selected['uri'], author['surname'] + ", " + author['forename'] )
                
            if need_new_concept:
                print "Ok, you need a new concept."
                created = False
                
                while not created:
                    user_uri = raw_input("Please add a new concept to ConceptPower, and enter the URI here: ")
                    if user_uri:
                        user_concept = cp.get(user_uri)             # Look up the URI that the user entered
                        if user_concept is None:
                            print "You lazy lump."                      # Couldn't find the URI. The user lies.
                        else:
                            print "Ok, we'll use this one."
                            concept_uri = user_uri                              # Using the ConceptPower URI that the user just created
                            author_title = user_concept[0][1].text
                            map.add ( user_uri, author['surname'] + ", " + author['forename'] )
                            created = True
                            
        # Second, we need to find the corresponding node (if there is one) in the Neo4j graph. If there isn't one, we'll create a new node.
        au_node = get_node (concept_uri)

        if au_node is None:                                         # If there is no node in Neo4j for the author, then we create a new one.
            print "Create: "
            print ({'uri': concept_uri, 'title': author_title, 'type': 'Person'})
            create_node ({'uri': concept_uri, 'title': author_title, 'type': 'Person'})
            au_node = get_node (concept_uri)
        
  
        # Third, we need to check whether there is a relationship between the author and the paper in the Neo4j graph. If there isn't, we'll create a relationship.
        graph_db = neo4j.GraphDatabaseService("http://localhost:7474/db/data")
        query = 'START n=node:node_auto_index(uri="'+concept_uri+'") MATCH (x)-[:hasAuthor]->(n) RETURN x'
        data, metadata = cypher.execute(graph_db, query)
        
        print node[0][0]
        
        rel_exist = False
        if len (data) > 0:
            for result in data:
                if result[0]['uri'] == paper['uri']:
                    rel_exist = True
        if not rel_exist:
            print 'Creating new relation.'
            rel = node[0][0].create_relationship_to(au_node[0][0], "hasAuthor")
                #graph_db.get_or_create_relationships((node[0][0], "hasAuthor", au_node[0][0]))
        else:
            print 'Relationship already exists. Skipping.'