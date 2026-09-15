# ADR-007 — Implement software now; retain physical acceptance gates

Status: accepted following user instructions to implement all phases and proceed
with simulation until hardware details are supplied.

## Decision

Implement the modular firmware and the host pipeline across phases. Exercise
transport, storage, DSP, ML, state control and UI using explicitly generated data.
Preserve separate source labels and prohibit synthetic models in physical inference.
Do not present software tests as physical system acceptance.

## Consequences

The project can be run and reviewed before the rig is available. Simulation does
not establish electrical compatibility, timing fidelity, sensor calibration,
mechanical safety or diagnostic performance. Hardware tests proceed in order once
the exact modules and safe fixture are identified. The original brief's phase gate
remains useful for physical acceptance; it no longer blocks software scaffolding
and implementation explicitly requested by the user.
