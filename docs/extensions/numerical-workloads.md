# Deferred numerical workload candidates

> Non-normative research disposition. The [first-release boundary](../language/first-release.md#release-boundary) and [primitive semantics](../language/first-release.md#primitive-semantics) own supported behavior. The [plan](../../PLAN.md#deferred-numerical-workload-selection) owns selection and commissioning. No numerical workload or floating-point extension is selected here.

## e-means research disposition

Reviewed 2026-11-09 against Bessa et al., [e-means: outperforming k-means (in one-tenth the epochs), arXiv:2611.09501v1](https://arxiv.org/html/2611.09501v1). The [project site](https://e-means.github.io/) is a discovery link; the versioned paper is the evidence read here.

The method trains k-means clusters using mini-batch exponential moving averages
of counts and sums, scheduled decay, dead-cluster revival and finalization.
The authors report matching the held-out loss of 25 Lloyd iterations in
1.4–2.6 dataset passes, with roughly 10–45× GPU speedups on their evaluated
configurations. Their GPU measurements use H100s. These results concern cluster
training; they establish no Vela implementation, universal convergence or
clustering-quality theorem, target timing bound, query-speed improvement or
inference-throughput improvement.

**Disposition: retain a future bounded numerical verification candidate.** An
actual search-index or quantization-codebook consumer could exercise explicit
storage, dimension and index invariants, finite iteration, mutable reductions
and numerical refinement. VerifiedOS's [e-means assessment](https://github.com/symbiogenesis/VerifiedOS/blob/main/docs/performance/e-means-assessment.md#consumer-selection-and-acceptance)
owns platform consumer selection and target evidence. Vela owns only the
additional language interpretation, authoring and lowering work a selected client
needs. Neither repository's research disposition commissions the other's work.

## Selection and prerequisites

The [first release](../language/first-release.md#primitive-semantics) excludes
runtime floating point. Keep that boundary: mathematical vectors and parsed
numeric syntax do not provide represented numerical libraries. A faithful
floating-point client needs a separately reviewed format and operation contract,
constant/runtime agreement and target correspondence through the
[required compiler route](../assurance/verification-strategy.md#compiler-route-decision). A fixed-point
variant instead needs explicit scales, ranges, rounding and overflow behavior,
and its own accuracy evaluation; the paper's measurements do not transfer to it.

Select a pilot only after a named application needs clustering, its input and
output contract is independently frozen, and the needed represented arithmetic,
sequence libraries and compiler joins are qualified. Compare the supported
subset and existing qualified implementation before adding language machinery.
Price the bounded pilot and any missing numerical semantics separately in
[PLAN.md](../../PLAN.md#deferred-numerical-workload-selection) before implementation.
Missing prerequisites leave the candidate deferred and preserve the supported
release's delivery order and independent-client selection.

## Bounded pilot acceptance

Start with one assignment-and-update kernel and an independently authored oracle.
Freeze the following contract before candidate implementation:

| Boundary | Required evidence for a selected pilot |
| --- | --- |
| Shape and storage | Declared dimensions, cluster and batch counts, caller-supplied capacities, initialized extents, aliasing and scratch/stack limits; prove all accesses and writes fit, including refused inputs and unchanged surrounding storage. |
| Finite execution | A fixed batch/epoch budget, bounded revival/finalization work and explicit capacity/exhaustion results; a quality-based stopping condition supplies no execution bound. |
| Reproducibility | Seed and shuffle inputs, tie-breaking, assignment policy, reduction order, decay schedule and finalization choice are part of the contract; repeatability is qualified at the selected arithmetic and target. |
| Numerical behavior | Handle empty/dead clusters, zero or underflowed denominators, overflow and rounding; floating point additionally covers the selected non-finite and exception behavior. Prove the implemented operations refine their declared numerical specification. |
| Independent judgment | Compare with the frozen oracle on tiny exhaustive and representative cases; include equal distances, empty clusters, boundary capacities, invalid shapes and changed-operation controls. Unsupported syntax and compilation failures supply no semantic verdict. |
| Artifact and benefit | Retain checked source correspondence, required resource/security evidence and exact-artifact lowering through the existing route. Measure authoring/proof cost, memory and target execution separately from clustering loss on held-out data at a declared baseline and threshold. |

A successful pilot establishes only its declared behavior and evidence endpoint.
Any clustering-quality, convergence, search-recall or compression claim needs its
own stated metric and evidence. H100 speedup factors supply no Vela or VerifiedOS
performance credit. Upstream source incorporation, if subsequently selected,
requires its revision-specific licence and dependency review under the
[working rules](../../AGENTS.md#before-incorporating-an-upstream).
