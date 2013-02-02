import os
import sys
from py2neo import neo4j, cypher
import unicodedata
from pprint import pprint
import urllib2

graph_db = neo4j.GraphDatabaseService("http://localhost:7474/db/data")
query = 'START n=node:node_auto_index(uri="http://www.digitalhps.org/concepts/066efc74-8710-4a1f-9111-3a27d880438e") MATCH (x)-[:hasAuthor]->(n) RETURN x'


    
data, metadata = cypher.execute(graph_db, query)

for node in data:
    print node[0]['uri']
