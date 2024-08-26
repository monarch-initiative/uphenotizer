
-- requires using jq to extract .data from the json into its own file:
create or replace table sgd_phenotype_json as select * from 'data/PHENOTYPE_SGD_DATA.json';
create or replace table apo_nodes as select id, name from read_csv('data/apo_kgx_tsv_nodes.tsv', delim='\t', ignore_errors=true);
create or replace table apo_pato as select * from 'data/apo_pato.sssom.tsv';

create or replace table sgd_phenotype as
select distinct
            (sgd_phenotype_json->>'$.phenotypeTermIdentifiers[*].termId'->>1)::VARCHAR as entitiy_id,
             NULL::VARCHAR as entity_label,
            (sgd_phenotype_json->>'$.phenotypeTermIdentifiers[*].termId'->>0)::VARCHAR as quality_id,
              NULL::VARCHAR as quality_label,
             list_distinct(sgd_phenotype_json->>'$.conditionRelations[*].conditions[*].chemicalOntologyId') as chemical_ids,
             list_transform(list_filter(sgd_phenotype_json->>'$.conditionRelations[*].conditions[*].conditionStatement', x -> x like 'chemical:%'), x -> replace(x,'chemical:','')) as chemical_labels,
             NULL::VARCHAR as pato_id,
             NULL::VARCHAR as pato_label,
      from sgd_phenotype_json;

-- update sgd_phenotype with apo labels for entity and quality
update sgd_phenotype
    set entity_label = apo_nodes.name
from apo_nodes
where entitiy_id = apo_nodes.id;

update sgd_phenotype
    set quality_label = apo_nodes.name
from apo_nodes
where quality_id = apo_nodes.id;

-- update sgd_phenotype table setting pato_id and pato_label
update sgd_phenotype
    set pato_id = apo_pato.object_id,
    pato_label = apo_pato.object_label
from apo_pato
where quality_id = apo_pato.subject_id
    and predicate_id = 'skos:exactMatch';

copy (
    select * REPLACE (list_aggregate(chemical_ids, 'string_agg', '|')  as chemical_ids,
                                    list_aggregate(chemical_labels, 'string_agg', '|') as chemical_labels)
    from sgd_phenotype
    where len(chemical_ids) < len(chemical_labels)
) to 'sgd_phenotype_missing_chemical_ids.tsv' (delimiter '\t');

copy (
        select * REPLACE (list_aggregate(chemical_ids, 'string_agg', '|')  as chemical_ids,
                                    list_aggregate(chemical_labels, 'string_agg', '|') as chemical_labels)
    from sgd_phenotype
    where len(chemical_ids) = len(chemical_labels)
) to 'sgd_phenotype.tsv' (delimiter '\t');


