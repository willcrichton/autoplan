#![feature(generic_associated_types, associated_type_defaults)]
#![allow(warnings)]

use pyo3::wrap_pyfunction;
use pyo3::{prelude::*, types::PyList};
use pythonize::depythonize;

use grammar::GrammarLearner;

mod grammar;
mod karel;

/// Formats the sum of two numbers as string.
#[pyfunction]
fn test(progs: &PyList) -> PyResult<()> {
  let progs = progs
    .iter()
    .map(|prog| depythonize::<karel::Statement>(prog))
    .collect::<Result<Vec<_>, _>>()?;

  let mut learner = GrammarLearner::build_lgcg(progs);
  learner.mcmc(1000);

  Ok(())
}

/// A Python module implemented in Rust.
#[pymodule]
fn grammar_induction(py: Python, m: &PyModule) -> PyResult<()> {
  m.add_function(wrap_pyfunction!(test, m)?)?;

  Ok(())
}
