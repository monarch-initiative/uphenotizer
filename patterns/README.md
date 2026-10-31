# Local patterns

DOSDP patterns that uphenotizer needs but uPheno doesn't have yet. Put one `<patternName>.yaml`
here per pattern, written as it would be in uPheno. Rows routed to a local pattern go to
`output/pending/<patternName>.tsv` instead of `output/patterns/`.

When the pattern lands in uPheno (`src/patterns/dosdp-patterns/`), delete it here. The next run then
moves its rows into `output/patterns/` automatically, because uPheno patterns take precedence over local ones.
