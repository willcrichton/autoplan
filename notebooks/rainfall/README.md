# Rainfall code classification

This series of notebook experiments is for automatic classification of student strategies in solving the "Rainfall" problem described in "The Recurring Rainfall Problem" (Fisler '14). The rainfall programming problem is to take a list of integers, and compute the average of all positive integers appearing before a sentinel value. In the ICER'14 paper, Fisler found three main plans/strategies in student solutions:

![](strategies.png)

Our goal is to implement a model that, given a student solution, can classify its structure as one of these three categories.

## Dataset

The dataset consists of around 400 solutions to the Rainfall problem in a variety of functional languages (OCaml, Pyret, and Racket), and about half are labeled with their plan.

![](dataset.png)

## Experiments

At a high level, our approach is to apply the various methods described in the ["Generative Grading"](http://arxiv.org/abs/1905.09916) paper, starting with the simplest approach and increasing in complexity based on what works.

* [Simple classifier trained on labeled student data](supervised_simple_classifier.ipynb)
