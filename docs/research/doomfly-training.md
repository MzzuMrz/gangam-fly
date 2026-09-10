# What DOOMFLY actually trained

Audited 2026-09-10. Local reference commit:
`71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33`. A read-only upstream check also found
no demonstrated-learning claim in the current README. No vendor files changed.

## Finding

DOOMFLY does not provide evidence that this kind of connectome experiment learns
quickly. Its public record labels the active training hypothesis unvalidated.
Working execution, changing synapses and learned useful behavior are separate
claims. [Repository README](https://github.com/nftechie/doomfly/blob/71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33/README.md)

## Actual live protocol

The September 5 live configuration injects real rendered RGB into 3,335 R1–R6 and
811 inferred R8 inputs of the 166,700-neuron network. Nonfatal damage schedules an
artificial 200 ms input to PPL101 cells 11327 and 11900. Actual KC/DAN activity drives
4,184 existing KC→MBON11 edges. The fixed DNp20/DNpe017 decoder is an engineering
mapping; game health/reward never directly chooses actions. The live version
preserves neural state, memory traces and decoder state between rounds, whereas
historical evaluation trials reset fast state while retaining learned efficacies.
These protocols must not be pooled.
[Live protocol](https://github.com/nftechie/doomfly/blob/71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33/docs/doom-live-training.md)

Its centered anti-Hebbian candidate uses KC/DAN eligibility traces and a two-state
memory system. The documented eta is 0.001, trace constants 1 s, memory decay 1800 s,
efficacy filter 50 ms and bounded efficacy 0.1–2× original strengths. These are
model assumptions, not validated settings for our body or task.
[Actual rule](https://github.com/nftechie/doomfly/blob/71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33/doom_learning_v6/rule.py)

## Two campaigns that must not be confused

| Campaign | Recorded result | Measured speed |
| --- | --- | --- |
| Earlier `gamma1-eligibility-ltd-v1`, training 41031/41032, evaluation 61031/61032, 12 s horizon | 22 episodes; training produced zero KC spikes and zero memory changes | 260.91 neural s / 1240.76 wall s = 0.210× |
| `adaptive-centered-v6`, training 41041, evaluation 61041/61042, 8 s horizon |Plastic training changed 1,862 edges. On 61041 plastic/shuffled died at 3.657 s while frozen reached 8 s; on 61042 all arms died at 3.657 s. Memory erasure reproduced the frozen trajectory. | 80.2282 neural s including warmup / 490.74 wall s = 0.163× |

The earlier pilot is documented in the
[review](https://github.com/nftechie/doomfly/blob/71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33/docs/doom-learning-review.md).
The v6 results belong to the
[iteration log](https://github.com/nftechie/doomfly/blob/71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33/docs/doom-learning-iteration-log.md)
and [v6 pilot artifacts](https://github.com/nftechie/doomfly/tree/71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33/outputs/doom-learning/physiology-v6/survival-pilot).
Neither establishes beneficial learning. The 22-episode `publication-v12.json`
record is not the v6 pilot.

The corrected benchmark reports individual throughput 0.117–0.506× and aggregate
parallel runtime 24.86 s versus 27.84 s serial (about 1.12×). Its authors reject the
previous 2.8× interpretation because startup and host load confounded it. Those
numbers measure simulation execution, not time to acquire a behavior.
[Benchmark discussion](https://github.com/nftechie/doomfly/blob/71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33/docs/doom-learning-review.md)

## What transfers to GangnamFly

Our implementation uses 56,850 existing incoming VNC motor edges with a global
reward-centered binned Hebbian hypothesis, approximately 400 ms eligibility,
eta 0.02 and 0.5–1.5× bounds. It resets fast neural state and eligibility each trial,
retaining weights. It does not use DOOMFLY's KC→MBON learning circuit or DAN-gated
memory rule. These eta values have different meanings and cannot be compared as
learning-speed multipliers. Sources: `gangnamfly/plasticity.py`, `brain.py`,
`experiment.py` and `training.py`.

Concrete next experiments, without altering the current running learner:

1. Continue matched frozen evaluations, and add an isolated **shuffled teaching
   signal** arm with equal exposure/duration, identical initial weights and matched
   seeds. A reward gain alone cannot establish causal learning.
2. For an apparent improvement, erase learned weights in a separate control and
   repeat held-out trials. Keep the live checkpoint intact.
3. Check whether the actual presynaptic/motor populations and eligibility traces
   vary enough to distinguish actions. Our `tanh(counts)` coactivity can saturate;
   that is a hypothesis to measure, not an established cause of failure.
4. Benchmark neural integration, physical integration and observation overhead
   separately on the same workload; do not infer improvement from a prettier FPS
   display or parallel aggregate throughput.
5. Treat biologically motivated KC→MBON/DAN plasticity as a separate calibrated
   experiment, not a drop-in proven fix for learning 30 joint actuators.

The new frontend therefore exposes actual published activity and labels rates,
spike totals and weight updates without calling them learned behavior. No learning
rule, checkpoint, neural timestep or motor mapping was changed for this feature.
