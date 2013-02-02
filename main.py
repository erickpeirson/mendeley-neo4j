from pprint import pprint
from mendeley_client import *
import os
import sys
import urllib2

import cmd

import xml.etree.ElementTree as ET

from py2neo import neo4j, cypher

# All-purpose script for searching lists of objects
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
        return False
        
    def get (self, uri):
        response = urllib2.urlopen(self.server+"Concept?id="+uri).read()
        root = ET.fromstring(response)
        if len(root) > 0:
            return root
        return False
    


def get_node_by_uri (gdb, uri):
    query = "START a=node(*) WHERE a.uri = '"+uri+"' RETURN a"
    data, metadata = cypher.execute(gdb, query)
    if data:
        return data
    return False


def process_author(cp, graph_db, author_pattern):

    # Checks ConceptPower for a match based on last name
    # Asks user which match (if any) is correct
    # If user selects one of the options...
    #   ...check whether a node with that URI exists in the graph, 
    #   if doesn't exist...
    #       ...create a new node in the graph
    #   if it does exist...
    # If user selects no option...
    #       ...ask for a ConceptPower URI
    #       ...validate the URI, and proceed
    #


    root = cp.search (author_pattern)

    if len(root) > 0:       # Find anything?
        i = 0
        options = []

        for child in root:
            if child.tag == "{http://www.digitalhps.org/}conceptEntry":
                options.append({'id': i, 'title': child[1].text, 'uri': child[0].text})
                i += 1
        options.append({'id': i, 'title': '--None of these--'})

        print "Possible matches found in ConceptPower: "        # Here are your options, user...
        for opt in options:
            print str(opt['id']) + " : " + opt['title']
        choice = raw_input("Please make a selection: ")         # Ask user for selection...

        selected = ol_get(options, lambda x: x['id'] == int(choice))
        
        if not selected:                                        # Dipshit
            print "Invalid selection!"
        else:                                                   # User didn't like the options
            if selected['title'] == "--None of these--":      
                print "Ok, you need a new concept."
                user_uri = raw_input("Please add a new concept to ConceptPower, and enter the URI here: ")
                if user_uri:
                    user_concept = cp.get(user_uri)             # Look up the URI that the user entered
                if not user_concept:
                    print "You lazy lump."                      # Couldn't find the URI. The user lies.
                else:
                    print "Ok, we'll use this one."
            else:
                print "Ok, we'll use this one."
                
                node = get_node_by_uri(graph_db, selected['uri'])
                if node:
                    return node
                else:
                    print "No such node exists in the graph. Creating a new node with title: (" + selected['title'] + ") and URI (" + selected['uri'] + ")..."

                    # Add a new node to Neo4j for the author
                    #query = "create n = {title: '"+selected['title']+"', uri: '"+selected['uri']+"', type: 'Person'} return n"
                    #print query
                    #data, metadata = cypher.execute(graph_db, query)
                    #if data:
                    #    print "Success!"
                    #    return get_node_by_uri(graph_db, selected['uri'])
                    #else:
                    #    print "Error adding node. :S"

    else:                   # Nothing found
        print "asdf"
        

def process_paper(cp, graph_db, m_prefix, document):
    node = get_node_by_uri(graph_db, m_prefix+str(document['id']))
    print node
    
    #for author in document['authors']:
        #au_node = process_author (cp, graph_db, author['surname'])
        #print au_node
    



    
graph_db = neo4j.GraphDatabaseService("http://localhost:7474/db/data/")
cp = ConceptPower()

uri_prefix = "http://open.mendeley.com/library/document/"

#documents = mendeley.library(items=100)
#pprint (documents)

#folders = mendeley.folders()
#pprint(folders)

#documents = mendeley.folder_documents('40139031',items=57)
#pprint (documents)

#for entry in documents['document_ids']:
    document = mendeley.document_details(entry)
    #print document['id']
    #process_paper(cp, graph_db, uri_prefix, document)



# Check to see if a paper is already in Neo4j




#process_author(cp, graph_db, 'Bradshaw')

