use float_ord::FloatOrd;
use itertools::Itertools;
use rand::{
  distributions::{Bernoulli, Distribution},
  rngs::StdRng,
  seq::{IteratorRandom, SliceRandom},
  Rng, SeedableRng,
};
use rayon::prelude::*;
use rustc_hash::{FxHashMap as HashMap, FxHashSet as HashSet};
use serde::Deserialize;
use std::any::Any;
use std::collections::hash_map::Entry;
use std::f64::NEG_INFINITY;
use std::fmt;
use std::mem;

#[derive(Hash, PartialEq, Eq, Clone, Copy, Default, Deserialize)]
pub struct Nonterminal(usize);

#[derive(Clone, PartialEq, Eq, Hash, Deserialize)]
#[serde(tag = "type", content = "data")]
pub enum SelfRef<T> {
  Abstract(Nonterminal),
  Concrete(Box<T>),
}

impl<T> SelfRef<T> {
  fn nonterminal(&self) -> Nonterminal {
    if let SelfRef::Abstract(nt) = self {
      *nt
    } else {
      panic!("SelfRef::nonterminal on Concrete")
    }
  }

  fn terminal(&self) -> &T {
    if let SelfRef::Concrete(t) = self {
      t
    } else {
      panic!("SelfRef::terminal on Abstract")
    }
  }
}

impl<T: fmt::Debug> fmt::Debug for SelfRef<T> {
  fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
    match self {
      SelfRef::Abstract(nt) => write!(f, "{:?}", nt),
      SelfRef::Concrete(t) => write!(f, "{:?}", t),
    }
  }
}

impl<T> Default for SelfRef<T> {
  fn default() -> Self {
    SelfRef::Abstract(Nonterminal::default())
  }
}

pub trait LabeledTree: Sized + Eq + Clone + fmt::Debug + Sync {
  fn label_matches(&self, other: &Self) -> bool;
  fn children<'a>(&'a self) -> Box<dyn Iterator<Item = &'a SelfRef<Self>> + 'a>;
  fn children_mut<'a>(&'a mut self) -> Box<dyn Iterator<Item = &'a mut SelfRef<Self>> + 'a>;

  fn matches(&self, other: &Self) -> bool {
    self.label_matches(other) && self.children().count() == other.children().count()
  }

  fn flatten(&self) -> (Vec<Vec<&Self>>, HashMap<(usize, usize, usize), usize>) {
    let mut levels = vec![vec![self]];
    let mut indices = vec![vec![((0, 0, 0), 0)]];

    loop {
      let last_level = levels.last().unwrap();
      let (next_level, next_indices) = last_level.iter().enumerate().fold(
        (Vec::new(), Vec::new()),
        |(mut level, mut indices), (i, node)| {
          let n = level.len();
          let (child_indices, child_nodes): (Vec<_>, Vec<_>) = node
            .children()
            .enumerate()
            .map(|(j, child)| (((levels.len() - 1, i, j), n + j), child.terminal()))
            .unzip();
          level.extend_from_slice(&child_nodes);
          indices.extend_from_slice(&child_indices);
          (level, indices)
        },
      );

      if next_level.len() == 0 {
        break;
      }

      levels.push(next_level);
      indices.push(next_indices);
    }

    let indices = indices
      .into_iter()
      .map(|indices| indices.into_iter())
      .flatten()
      .collect::<HashMap<_, _>>();

    (levels, indices)
  }
}

impl fmt::Debug for Nonterminal {
  fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
    write!(f, "F{}", self.0)
  }
}

#[derive(PartialEq, Eq, Clone)]
enum Token<T> {
  Nonterminal(Nonterminal),
  Terminal(T),
}

impl<T: LabeledTree> Token<T> {
  fn substitute(&mut self, from: Nonterminal, to: Nonterminal) {
    match self {
      Token::Nonterminal(nt) => {
        if *nt == from {
          *nt = to;
        }
      }
      Token::Terminal(t) => {
        for child in t.children_mut() {
          if let SelfRef::Abstract(nt) = child {
            if *nt == from {
              *nt = to;
            }
          } else {
            unreachable!()
          };
        }
      }
    }
  }

  fn substitute_maybe(&mut self, from: Nonterminal, to: Nonterminal, rng: &mut impl Rng) {
    if rng.gen::<bool>() {
      self.substitute(from, to);
    }
  }
}

impl<T: fmt::Debug> fmt::Debug for Token<T> {
  fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
    match self {
      Token::Nonterminal(nt) => write!(f, "{:?}", nt),
      Token::Terminal(t) => write!(f, "{:?}", t),
    }
  }
}

#[derive(Clone)]
struct Branch<T> {
  token: Token<T>,
  log_prob: f64,
}

impl<T: fmt::Debug> fmt::Debug for Branch<T> {
  fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
    write!(f, "{:?} [{:.3?}]", self.token, self.log_prob.exp())
  }
}

#[derive(Clone)]
struct Production<T> {
  name: Nonterminal,
  branches: Vec<Branch<T>>,
}

impl<T: LabeledTree> Production<T> {
  fn substitute(&mut self, from: Nonterminal, to: Nonterminal) {
    for branch in self.branches.iter_mut() {
      branch.token.substitute(from, to);
    }
  }

  fn substitute_maybe(&mut self, from: Nonterminal, to: Nonterminal, rng: &mut impl Rng) {
    for branch in self.branches.iter_mut() {
      branch.token.substitute_maybe(from, to, rng);
    }
  }
}

impl<T: fmt::Debug> fmt::Debug for Production<T> {
  fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
    write!(f, "{:?} -> ", self.name)?;
    for (i, branch) in self.branches.iter().enumerate() {
      if i > 0 {
        write!(f, " | ")?;
      }
      write!(f, "{:?}", branch);
    }
    Ok(())
  }
}

#[derive(Clone)]
pub struct Grammar<T> {
  productions: HashMap<Nonterminal, Production<T>>,
  nonterminal_counter: usize,
  root: Nonterminal,
}

pub struct GrammarLearner<T> {
  pub grammar: Grammar<T>,
  exemplars: Vec<T>,
  rng: StdRng,
}

impl<T: fmt::Debug> fmt::Debug for Grammar<T> {
  fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
    write!(f, "{:#?}", self.productions)
  }
}

impl<T: LabeledTree> Grammar<T> {
  fn new() -> Self {
    Grammar {
      productions: HashMap::default(),
      nonterminal_counter: 0,
      root: Nonterminal::default(),
    }
  }

  fn add_production(&mut self, branches: Vec<Branch<T>>) -> Nonterminal {
    let nt = self.new_nonterminal();
    self
      .productions
      .insert(nt, Production { name: nt, branches });
    nt
  }

  fn simplify(&mut self) {
    for prod in self.productions.values_mut() {
      prod.branches = prod
        .branches
        .clone()
        .into_iter()
        .enumerate()
        .filter(|(i, branch)| match &branch.token {
          Token::Nonterminal(nt) if *nt == prod.name => false,
          token
            if prod
              .branches
              .iter()
              .enumerate()
              .any(|(j, other_branch)| *i > j && other_branch.token == *token) =>
          {
            false
          }
          _ => true,
        })
        .map(|(_, branch)| branch)
        .collect();
    }
  }

  fn new_nonterminal(&mut self) -> Nonterminal {
    let n = self.nonterminal_counter;
    self.nonterminal_counter += 1;
    Nonterminal(n)
  }

  pub fn parse(&self, tree: &T) -> (f64, HashMap<Nonterminal, Vec<usize>>) {
    self.parse_rule(tree, self.root)
  }

  fn try_parse_branch(
    branch: &Branch<T>,
    node: &T,
    l: usize,
    i: usize,
    parses: &Vec<Vec<HashMap<Nonterminal, Vec<Vec<f64>>>>>,
    indices: &HashMap<(usize, usize, usize), usize>,
  ) -> Option<Vec<f64>> {
    let probs = match &branch.token {
      Token::Nonterminal(nt) => {
        let node_parses = &parses[l][i];
        node_parses.get(nt).map(|probs| {
          probs
            .clone()
            .into_iter()
            .map(|branch| branch.into_iter())
            .flatten()
            .collect::<Vec<_>>()
        })
      }
      Token::Terminal(t) => {
        if node.matches(t) {
          let n_children = t.children().count();
          if n_children == 0 {
            Some(vec![1_f64.ln()])
          } else {
            let children_parses = t
              .children()
              .enumerate()
              .filter_map(|(j, rule)| {
                let index = (l, i, j);
                let child_parses = &parses
                  .get(l + 1)
                  .expect("Level")
                  .get(*indices.get(&index).expect("Index"))
                  .expect("Child");
                child_parses.get(&rule.nonterminal()).clone()
              })
              .collect::<Vec<_>>();

            (children_parses.len() == n_children).then(|| {
              children_parses
                .into_iter()
                .map(|parses| {
                  parses
                    .into_iter()
                    .map(|branch| branch.into_iter())
                    .flatten()
                })
                .multi_cartesian_product()
                .map(|prob_combination| prob_combination.into_iter().sum())
                .collect::<Vec<_>>()
            })
          }
        } else {
          None
        }
      }
    };

    probs.map(|probs| {
      let branch_prob = branch.log_prob;
      probs
        .into_iter()
        .map(move |prob| prob + branch_prob)
        .collect()
    })
  }

  fn parse_rule(&self, tree: &T, rule: Nonterminal) -> (f64, HashMap<Nonterminal, Vec<usize>>) {
    let (levels, indices) = tree.flatten();
    // println!("levels: {:#?}", levels);
    // println!("indices: {:?}", indices);

    let mut parses = levels
      .iter()
      .map(|level| {
        level
          .iter()
          .map(|node| HashMap::default())
          .collect::<Vec<_>>()
      })
      .collect::<Vec<_>>();

    let update_parse =
      |node_parses: &mut HashMap<Nonterminal, Vec<Vec<f64>>>, probs: Vec<Vec<f64>>, nt| -> bool {
        let entry_len = |entry: &Vec<Vec<f64>>| entry.iter().map(|v| v.len()).sum::<usize>();
        let n_matches = entry_len(&probs);
        if n_matches > 0 {
          match node_parses.entry(nt) {
            Entry::Vacant(vacancy) => {
              vacancy.insert(probs);
              true
            }
            Entry::Occupied(mut entry) => {
              if entry_len(entry.get()) < n_matches {
                entry.insert(probs);
                true
              } else {
                false
              }
            }
          }
        } else {
          false
        }
      };

    for l in (0..levels.len()).rev() {
      let level = &levels[l];

      let mut level_iters = 0;
      loop {
        let mut change = false;

        for (i, node) in level.iter().enumerate() {
          for prod in self.productions.values() {
            let probs = prod
              .branches
              .iter()
              .map(|branch| {
                Self::try_parse_branch(&branch, node, l, i, &parses, &indices)
                  .unwrap_or_else(Vec::new)
              })
              .collect::<Vec<_>>();

            let node_parses = &mut parses[l][i];
            if update_parse(node_parses, probs, prod.name) {
              change = true;
            }
          }
        }

        level_iters += 1;

        if !change || level_iters >= self.productions.len() {
          break;
        }
      }
    }

    let mut parse_counts = self
      .productions
      .iter()
      .map(|(k, p)| (*k, [0].repeat(p.branches.len())))
      .collect::<HashMap<_, _>>();
    for level_parses in parses.iter() {
      for node_parses in level_parses.iter() {
        for (nt, nt_parses) in node_parses.iter() {
          let nt_counts = parse_counts.get_mut(nt).unwrap();
          for (i, branch_parses) in nt_parses.iter().enumerate() {
            nt_counts[i] += branch_parses.len();
          }
        }
      }
    }

    // println!("levels {:?}", levels);
    // println!("indices {:?}", indices);
    // println!(
    //   "parses {:.3?}",
    //   parses
    //     .clone()
    //     .into_iter()
    //     .map(|level| {
    //       level
    //         .into_iter()
    //         .map(|map| {
    //           map
    //             .into_iter()
    //             .map(|(k, vs)| {
    //               (
    //                 k,
    //                 vs.into_iter()
    //                   .map(|v| v.into_iter().map(|p| p.exp()).collect::<Vec<_>>())
    //                   .collect::<Vec<_>>(),
    //               )
    //             })
    //             .collect::<HashMap<_, _>>()
    //         })
    //         .collect::<Vec<_>>()
    //     })
    //     .collect::<Vec<_>>()
    // );

    let root_parse = &parses[0][0];
    let total_prob = if let Some(parse) = root_parse.get(&self.root) {
      parse
        .iter()
        .map(|branch| branch.iter())
        .flatten()
        .map(|p| p.exp())
        .sum::<f64>()
        .ln()
    } else {
      0_f64.ln()
    };

    (total_prob, parse_counts)
  }
}

// Concentration parameter for production weights
// ALPHA > 1 means prefer equal probabilities, ALPHA < 1 means prefer concentrated probabilities
const ALPHA: f64 = 1.0;

// Parameter for grammar prior
const LAMBDA: f64 = 1.5;

impl<T: LabeledTree + fmt::Debug> GrammarLearner<T> {
  pub fn build_lgcg(exemplars: Vec<T>) -> Self {
    let mut this = GrammarLearner {
      grammar: Grammar::new(),
      exemplars: exemplars.clone(),
      rng: StdRng::from_seed([0; 32]),
    };

    let n = exemplars.len();
    let branches = exemplars
      .into_iter()
      .map(|exemplar| {
        let nt = this.build_lgcg_exemplar(exemplar);
        Branch {
          log_prob: (1. / (n as f64)).ln(),
          token: Token::Nonterminal(nt),
        }
      })
      .collect::<Vec<_>>();

    let root = this.grammar.add_production(branches);
    this.grammar.root = root;

    this
  }

  fn build_lgcg_exemplar(&mut self, mut exemplar: T) -> Nonterminal {
    for child in exemplar.children_mut() {
      let child_owned = mem::take(child);
      let child_nt = if let SelfRef::Concrete(subtree) = child_owned {
        self.build_lgcg_exemplar(*subtree)
      } else {
        panic!("Abstract in exemplar")
      };

      *child = SelfRef::Abstract(child_nt);
    }

    let token = Token::Terminal(exemplar);
    if let Some((nt, _)) = self
      .grammar
      .productions
      .iter()
      .find(|(k, v)| v.branches[0].token == token)
    {
      *nt
    } else {
      self.grammar.add_production(vec![Branch {
        log_prob: 1_f64.ln(),
        token,
      }])
    }
  }

  pub fn grammar_prior(&self) -> f64 {
    self.structure_prior() + self.param_prior()
  }

  pub fn structure_prior(&self) -> f64 {
    let length = self.grammar.productions.len() as f64;
    -(length.powf(LAMBDA))
  }

  fn param_prior(&self) -> f64 {
    self
      .grammar
      .productions
      .values()
      .fold(1_f64.ln(), |acc, prod| {
        prod
          .branches
          .iter()
          .map(|branch| {
            if branch.log_prob != NEG_INFINITY {
              branch.log_prob * (ALPHA - 1.)
            } else {
              branch.log_prob
            }
          })
          .sum::<f64>()
          + acc
      })
  }

  pub fn posterior(&self) -> f64 {
    self.data_likelihood() + self.grammar_prior()
  }

  pub fn data_likelihood(&self) -> f64 {
    self
      .exemplars
      .par_iter()
      .map(|exemplar| self.grammar.parse(exemplar).0)
      .sum()
  }

  fn merge(&mut self, src: Nonterminal, dst: Nonterminal) {
    let src_prod = self.grammar.productions.remove(&src).unwrap();
    let dst_prod = self.grammar.productions.get_mut(&dst).unwrap();
    dst_prod.branches.extend(src_prod.branches.into_iter());

    let src_name = src_prod.name;
    let dst_name = dst_prod.name;
    for prod in self.grammar.productions.values_mut() {
      prod.substitute(src_name, dst_name);
    }

    if src == self.grammar.root {
      self.grammar.root = dst;
    }

    self.grammar.simplify();
  }

  fn split(&mut self, nt: Nonterminal) {
    let prod = self.grammar.productions.get_mut(&nt).unwrap();
    prod.branches.shuffle(&mut self.rng);
    let pivot = self.rng.gen_range(1..prod.branches.len());
    let split_branches = prod.branches.drain(0..pivot).collect::<Vec<_>>();

    let new_nt = self.grammar.new_nonterminal();
    self.grammar.productions.insert(
      new_nt,
      Production {
        name: new_nt,
        branches: split_branches,
      },
    );

    for prod in self.grammar.productions.values_mut() {
      prod.substitute_maybe(nt, new_nt, &mut self.rng);
    }
  }

  pub fn merge_random(&mut self) {
    let nts = self
      .grammar
      .productions
      .keys()
      .choose_multiple(&mut self.rng, 2);
    if nts.len() == 2 {
      self.merge(*nts[0], *nts[1]);
    }
  }

  pub fn split_random(&mut self) {
    let nt = self
      .grammar
      .productions
      .iter()
      .filter_map(|(k, v)| (v.branches.len() > 1).then(|| k))
      .choose(&mut self.rng);
    if let Some(nt) = nt {
      self.split(*nt);
    }
  }

  pub fn update_params(&mut self) {
    let mut last_counts = None;
    loop {
      let parse_counts = self
        .exemplars
        .par_iter()
        .map(|exemplar| {
          let (_, parse_counts) = self.grammar.parse(exemplar);
          parse_counts
        })
        .reduce_with(|mut h1, h2| {
          for (k, vs) in h2.into_iter() {
            for (v1, v2) in h1.get_mut(&k).unwrap().iter_mut().zip(vs.into_iter()) {
              *v1 += v2;
            }
          }
          h1
        });

      if last_counts == parse_counts {
        break;
      }

      let parse_counts = parse_counts.unwrap();
      for (nt, production) in self.grammar.productions.iter_mut() {
        let counts = &parse_counts[nt];
        let total = counts.iter().sum::<usize>() as f64;

        for (count, branch) in counts.iter().zip(production.branches.iter_mut()) {
          branch.log_prob = if total > 0. {
            (*count as f64 / total).ln()
          } else {
            (1. / (counts.len() as f64)).ln()
          };
        }
      }

      last_counts = Some(parse_counts);
    }
  }

  pub fn mcmc(&mut self, iterations: usize) {
    let mut i = 0;

    let mut history = Vec::new();

    loop {
      //println!("Current grammar: {:#?}", self.grammar);

      let last_posterior = self.posterior();
      let last_grammar = self.grammar.clone();

      if self.rng.gen::<bool>() {
        //println!("Split!");
        self.split_random();
      } else {
        //println!("Merge!");
        self.merge_random();
      }

      self.update_params();

      let new_posterior = self.posterior();

      // TODO: incorporate Q term into acceptance
      let cooling = 1_f64 / ((i + 1) as f64);
      let acceptance = (new_posterior * cooling - last_posterior * cooling)
        .exp()
        .min(1.);
      println!(
        "acceptance {:.5?}, new {:.5?}, last {:.5?}",
        acceptance, new_posterior, last_posterior
      );

      if Bernoulli::new(acceptance).unwrap().sample(&mut self.rng) {
        println!("Accept");
        //println!("{:?}", self.grammar);
        history.push((last_grammar, last_posterior));
        // we're good
      } else {
        println!("Not accept");
        // rollback
        self.grammar = last_grammar;
      }

      i += 1;

      if i > iterations {
        break;
      }
    }

    let (best_grammar, best_posterior) = history
      .iter()
      .max_by_key(|(_, posterior)| FloatOrd(*posterior))
      .unwrap();
    println!(
      "all posteriors {:?}",
      history.iter().map(|(_, p)| p).collect::<Vec<_>>()
    );
    println!("best grammar ({:?}) {:#?}", best_posterior, best_grammar);
  }
}
