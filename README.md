mendeley-neo4j
==============

An experimental python script that reads papers from Mendeley via its online API, and creates nodes/relationships in Neo4j between papers and authors. All nodes have a property 'uri', which is a Mendeley URL for papers. ConceptPower is used as an authority for persons.