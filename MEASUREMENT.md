# Measurement Plan: Shared Mental Model Quality

## Goal

Explain the treatment performance pattern through the quality of the shared
mental model (SMM) produced under each input-context condition.

The key requirement is that the metric must be computed from the archived SMM
memory markdown files, because the memory markdown is the explicit SMM artifact
changed by the input-context manipulation.

## Problem With the Existing Metric

The current `smm_evidence_share` metric counts whether decisive Candidate C
evidence appears anywhere in the three memory files. This is useful, but it is
too broad for explaining the observed performance pattern.

In `backup_01`, low and high are close on raw evidence coverage, while their
decision performance differs strongly. Therefore, raw evidence coverage alone
cannot be the central explanatory metric.

## Proposed Metrics

Use two separate metrics, because they measure different SMM constructs.

### 1. Active SMM Similarity

This is the pure sharedness metric.

Represent each agent's active SMM as a set of canonical task facts and decision
claims extracted from active decision-relevant memory sections. Then calculate
pairwise Dice similarity and average the three pairwise scores:

```text
Dice(A, B) =
  2 * |facts_A intersect facts_B|
  /
  (|facts_A| + |facts_B|)

Active SMM Similarity =
  mean(Dice(agent_1, agent_2),
       Dice(agent_1, agent_3),
       Dice(agent_2, agent_3))
```

This should replace whole-markdown embedding similarity when the goal is to
measure sharedness. Whole-markdown embeddings are inflated by template
similarity and can miss which task facts are actually shared.

### 2. Active Majority Shared Accuracy

This is the central explanatory quality metric.

```text
Active Majority Shared Accuracy =
  number of decisive Candidate C evidence facts represented as active
  decision evidence in at least 2 of 3 agent memory files
  /
  number of decisive Candidate C evidence facts
```

This metric combines two ideas:

- **Accuracy:** the SMM contains task-correct decisive evidence for Candidate C.
- **Sharedness:** the evidence is present in a majority of agent memories.

## What Counts as Active Decision Evidence

For the accuracy metric, a decisive Candidate C fact should count only if it
appears in a decision-relevant part of an agent's memory markdown:

- Candidate C row, `Discussed strengths`
- `Group Decision State`

It should not count merely because it appears somewhere in the file, for example
under unclear criteria, next discussion move, or unresolved questions. The point
is to measure whether the evidence is actively represented as part of the team's
decision model, not merely stored as background text.

For the similarity metric, extract active facts and decision claims from:

- Candidate rows, `Discussed strengths`
- Candidate rows, `Discussed concerns`
- `Group Decision State`
- optionally `Current Positions`

## Decisive Candidate C Evidence Set

Use the Candidate C facts that make Candidate C the correct hidden-profile
solution:

- Candidate C is 100% reliable.
- Candidate C creates a positive atmosphere with the crew.
- Candidate C keeps calm in a crisis.
- Candidate C understands complicated technology.
- Candidate C puts concern for others above everything.
- Candidate C has excellent attention skills.

## Composite SMM Quality

The optional composite metric is:

```text
Active SMM Quality =
  Active Majority Shared Accuracy
  *
  Active SMM Similarity
```

This composite is useful for reporting, but the main explanatory component is
`Active Majority Shared Accuracy`. The similarity term should be the active
fact-set similarity, not the existing whole-markdown embedding similarity.

## Interpretation

This metric is better aligned with shared mental model theory than raw evidence
coverage because it separates:

- whether the model is shared across agents,
- whether the shared content is task-correct,
- whether the content is active in the decision representation.

The expected argument is:

> Moderate context produces the best SMM quality because it best supports active
> shared representation of the decisive Candidate C evidence. High context may
> still contain relevant evidence somewhere in memory, but this evidence is less
> active in the decision-relevant parts of the SMM. Thus, high context can
> produce shared but less useful mental models.

## Prototype Result Pattern

A cleaned prototype extractor was run on `backup_01` and `backup_02`. It
normalizes Unicode spacing/hyphen variants, maps active memory text to canonical
task facts, and computes pairwise Dice similarity over the resulting fact sets.

```text
backup_01 treatment runs

Condition   Performance   Active SMM Similarity   Active Majority Accuracy   Active SMM Quality
low         0.72          0.608                   0.343                      0.216
moderate    0.74          0.622                   0.400                      0.251
high        0.49          0.673                   0.282                      0.192

Correlation with correct decision, backup_01:
whole-markdown embedding similarity   -0.002
active SMM similarity                  0.044
active majority shared accuracy        0.707
active SMM quality                     0.666

backup_02 moderate treatment runs

Performance                            0.74
Active SMM Similarity                  0.614
Active Majority Shared Accuracy        0.403
Active SMM Quality                     0.253

Correct vs. incorrect runs in backup_02:
Active Majority Shared Accuracy        0.482 vs. 0.180
Active SMM Quality                     0.340 vs. 0.124
```

This result is important: pure similarity does not explain the performance
boost. In `backup_01`, high has the highest active similarity but the lowest
decision performance. The performance-relevant difference is whether the shared
active model contains the decisive Candidate C evidence.

Therefore, the thesis argument should not be "moderate creates the most similar
SMM." The stronger argument is:

> Moderate creates the best active shared mental model quality because the
> team's shared active model contains more of the task-correct decisive evidence.
> High can create sharedness without accuracy: agents become more aligned, but
> around a less useful or incomplete decision model.

## Literature Grounding

The metric can be justified using the standard distinction in SMM research
between sharedness/similarity and accuracy/quality. A high-quality SMM should
not only be similar across team members; it should also accurately represent the
task-relevant content needed for performance.

Relevant grounding:

- Shared mental models are commonly evaluated in terms of both similarity among
  team members and accuracy relative to the task or expert model.
- Similarity alone is insufficient: team members can share an incomplete or
  wrong model.
- In this simulation, the expert/task model is defined by the hidden-profile
  solution: Candidate C is correct because of the distributed decisive evidence.

## Implementation Notes

1. For each run, read the three files in `shared_mental_models/`.
2. Normalize memory text before matching facts, especially Unicode spaces in
   strings such as `100 %` and nonstandard hyphen variants.
3. Map active memory text to canonical fact labels.
4. For similarity, calculate pairwise Dice similarity over each agent's active
   fact/claim set and average the three pairs.
5. For accuracy, check whether each decisive Candidate C fact appears in the active
   decision sections of each agent memory.
6. Mark the fact as shared if at least two of three agent memories contain it in
   those active sections.
7. Divide the number of shared decisive facts by the total number of decisive
   facts.
8. Optionally multiply `Active Majority Shared Accuracy` by `Active SMM
   Similarity`.
