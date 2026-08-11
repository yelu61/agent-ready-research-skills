# Notebook audit prompt

Audit the named notebook without changing it first. Report:

1. inputs, outputs and execution order;
2. hidden state and absolute paths;
3. raw versus transformed matrices;
4. experimental unit, groups and covariates;
5. stochastic steps and seeds;
6. cells not executed or inconsistent with saved outputs;
7. duplicated logic that belongs in a script;
8. reproducibility and scientific-interpretation risks.

Propose the smallest safe repair and the checks required after editing.
