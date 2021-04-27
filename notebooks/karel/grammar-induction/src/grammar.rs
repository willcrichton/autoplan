use itertools::Itertools;
use std::any::Any;
use std::collections::{HashMap, HashSet};
use std::fmt;
use std::mem;

#[derive(Hash, PartialEq, Eq, Clone, Copy, Default)]
pub struct Nonterminal(usize);

#[derive(Clone, PartialEq, Eq, Hash)]
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

pub trait LabeledTree: Sized + Eq + Clone {
  fn matches(&self, other: &Self) -> bool;
  fn children<'a>(&'a self) -> Box<dyn Iterator<Item = &'a SelfRef<Self>> + 'a>;
  fn children_mut<'a>(&'a mut self) -> Box<dyn Iterator<Item = &'a mut SelfRef<Self>> + 'a>;
}

impl fmt::Debug for Nonterminal {
  fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
    write!(f, "F{}", self.0)
  }
}

#[derive(Debug, PartialEq, Eq)]
enum Token<T> {
  Nonterminal(Nonterminal),
  Terminal(T),
}

struct Branch<T> {
  token: Token<T>,
  log_prob: f64,
}

impl<T: fmt::Debug> fmt::Debug for Branch<T> {
  fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
    write!(f, "{:?} [{:?}]", self.token, self.log_prob.exp())
  }
}

struct Production<T> {
  name: Nonterminal,
  branches: Vec<Branch<T>>,
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

#[derive(Debug)]
pub struct Grammar<T> {
  productions: HashMap<Nonterminal, Production<T>>,
  nonterminal_counter: usize,
  root: Nonterminal,
  exemplars: Vec<T>,
}

// Concentration parameter for production weights
// ALPHA > 1 means prefer equal probabilities, ALPHA < 1 means prefer concentrated probabilities
const ALPHA: f64 = 1.0;

// Parameter for grammar prior
const LAMBDA: f64 = 1.0;

impl<T: LabeledTree + fmt::Debug> Grammar<T> {
  pub fn build_lgcg(exemplars: Vec<T>) -> Self {
    let mut this = Grammar {
      productions: HashMap::new(),
      nonterminal_counter: 0,
      root: Nonterminal::default(),
      exemplars: exemplars.clone(),
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

    this.root = this.new_nonterminal();
    this.productions.insert(
      this.root,
      Production {
        name: this.root,
        branches,
      },
    );

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
      .productions
      .iter()
      .find(|(k, v)| v.branches[0].token == token)
    {
      *nt
    } else {
      let nt = self.new_nonterminal();
      self.productions.insert(
        nt,
        Production {
          name: nt,
          branches: vec![Branch {
            log_prob: 1_f64.ln(),
            token,
          }],
        },
      );
      nt
    }
  }

  fn new_nonterminal(&mut self) -> Nonterminal {
    let n = self.nonterminal_counter;
    self.nonterminal_counter += 1;
    Nonterminal(n)
  }

  pub fn grammar_prior(&self) -> f64 {
    self.structure_prior() + self.param_prior()
  }

  fn structure_prior(&self) -> f64 {
    let length = self
      .productions
      .values()
      .map(|prod| prod.branches.len())
      .sum::<usize>() as f64;
    (-length.log2()).powf(LAMBDA)
  }

  fn param_prior(&self) -> f64 {
    self.productions.values().fold(1_f64.ln(), |acc, prod| {
      prod
        .branches
        .iter()
        .map(|branch| branch.log_prob * (ALPHA - 1.))
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
      .iter()
      .map(|exemplar| {
        self
          .parse(exemplar)
          .iter()
          .map(|p| p.exp())
          .sum::<f64>()
          .ln()
      })
      .sum()
  }

  pub fn parse(&self, tree: &T) -> Vec<f64> {
    self.parse_rule(tree, self.root)
  }

  fn parse_rule(&self, tree: &T, rule: Nonterminal) -> Vec<f64> {
    let production = &self.productions[&rule];
    production
      .branches
      .iter()
      .filter_map(|branch| {
        let parse_probs = match &branch.token {
          Token::Nonterminal(nt) => Some(self.parse_rule(tree, *nt)),

          Token::Terminal(t) => tree.matches(t).then(|| {
            if tree.children().count() == 0 {
              vec![1_f64.ln()]
            } else {
              tree
                .children()
                .zip(t.children())
                .map(|(l, r)| self.parse_rule(l.terminal(), r.nonterminal()).into_iter())
                .multi_cartesian_product()
                .map(|branch_probs| {
                  branch_probs
                    .into_iter()
                    .fold(0., |prob, parse| prob + parse)
                })
                .collect::<Vec<_>>()
            }
          }),
        };

        parse_probs.map(|parse_probs| {
          let branch_prob = branch.log_prob;
          parse_probs.into_iter().map(move |prob| prob + branch_prob)
        })
      })
      .flatten()
      .collect()
  }
}
