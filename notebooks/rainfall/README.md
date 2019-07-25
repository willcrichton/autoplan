# Rainfall code classification

This series of notebook experiments is for automatic prediction of student strategies in solving the "Rainfall" problem described in "The Recurring Rainfall Problem" (Fisler '14). The problem is to take a list of integers, and compute the average of all positive integers appearing before a sentinel value. In the ICER'14 paper, Fisler found three main strategies:

![](strategies.png)

Our goal is to implement a model that, given a student solution, can classify its structure as one of these three categories.

## Dataset

The dataset consists of around 300 solutions to the Rainfall problem in a variety of functional languages (OCaml, Pyret, and Racket), and about half are labeled with their plan.

![](dataset.png)

## Experiments

* [Simple classifier trained on labeled student data](supervised_simple_classifier.ipynb)
* [Simple classifier trained on synthetic data](synthetic_simple_classifier.ipynb)
