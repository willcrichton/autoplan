# Autoplan

Autoplan is a Python library for using machine learning to classify programs into categories. We built Autoplan as a part of our work for the SIGCSE'21 paper [Automating Program Structure Classification](https://dl.acm.org/doi/10.1145/3408877.3432358).

## Installation

Right now, we only support installation from source, so follow the instructions below.

### From source

```
git clone https://github.com/willcrichton/autoplan
cd autoplan
pip3 install -e .
```

Several examples and modules use optional dependencies that are not automatically installed. If you want to run every possible autoplan example, run this:

```
pip3 install hyperopt nltk javalang
```


## Citation

```bibtex
@inproceedings{crichton2021automating,
  title={Automating Program Structure Classification},
  author={Crichton, Will and Sampaio, Georgia Gabriela and Hanrahan, Pat},
  booktitle={Proceedings of the 52nd ACM Technical Symposium on Computer Science Education},
  pages={1177--1183},
  year={2021}
}
```
