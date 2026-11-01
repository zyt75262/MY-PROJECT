# S.-T. Yau High School Science Award — Mathematical Modeling Project

## Project Overview

This project explores how tourist movement and residents' social tolerance can affect one another in a historic neighborhood. Using the Yinshanmen community in Zhenjiang, China, as a case study, I developed a mathematical modeling framework to examine visitor flow, changing social capacity, and possible crowd-management strategies.

The model represents the neighborhood as a directed network and connects pedestrian-flow dynamics with a time-varying measure of residents' tolerance. It also examines a sustainable visitor-arrival threshold and feedback-based admission and route-diversion strategies.

## Methods

- Dynamic network-flow modeling on a network of 16 nodes and 20 directed edges.
- State-dependent capacity and feedback between visitor exposure and residents' tolerance.
- Numerical simulations comparing three scenarios: an unconstrained baseline (A), a static-capacity strategy (B), and a state-dependent control strategy (C).
- Evaluation using five measures: peak density, time below the tolerance threshold, minimum tolerance, cumulative entrance waiting, and average time in the network.
- Independent verification and time-step sensitivity checks.

## Repository Contents

- **Simulation script (`simulation.py`):** Core network-flow model and scenario comparisons.
- **Verification and sensitivity scripts (`independent_verify.py`, `sensitivity_test*.py`):** Additional numerical checks.
- **JSON files:** Model parameters, network information, threshold calculations, and results for scenarios A, B, and C.
- **CSV file:** Summary of the five evaluation measures.

*Some uploaded filenames include a longer project prefix rather than the short names shown above.*

## Research Paper

[Read the accompanying S.-T. Yau research paper](../Tang_Ziyi_Yau_Science_Award_Submission_2026.pdf)

## Notes on Reproducibility

These files document the research simulations and their recorded outputs. Some scripts contain file paths specific to the original development environment and may require path and filename adjustments before they can be rerun elsewhere. The model is a case study; its results should not be interpreted as independently validated real-world forecasts.
