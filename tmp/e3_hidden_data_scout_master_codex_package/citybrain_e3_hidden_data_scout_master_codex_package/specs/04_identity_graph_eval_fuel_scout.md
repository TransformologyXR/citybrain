# Lane D — Identity / Graph Evaluation Fuel Scout

Find candidate fixtures for evaluating entity resolution and graph semantics.

## Candidate types

- positive same-entity candidates
- negative do-not-merge candidates
- ambiguous bridge candidates
- edge confidence challenge cases
- temporal edge validity cases
- geometry containment/adjoining conflict cases

## Required distinction

Do not treat a candidate bridge as fact. Keep:
- candidate
- reviewed
- promoted
- rejected
- disputed
