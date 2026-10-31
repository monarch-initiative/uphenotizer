PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

# Deprecated classes keep their generated label, prefixed with "obsolete " (OBO convention).
DELETE { ?c rdfs:label ?label }
INSERT { ?c rdfs:label ?obsolete }
WHERE {
  ?c owl:deprecated ?d ;
     rdfs:label ?label .
  FILTER(STR(?d) = "true" && !STRSTARTS(STR(?label), "obsolete "))
  BIND(CONCAT("obsolete ", STR(?label)) AS ?obsolete)
}
