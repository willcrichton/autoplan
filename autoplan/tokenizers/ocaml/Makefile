all: tokenize.native preprocess.native

%.native: %.ml
	ocamlbuild -use-ocamlfind $*.native

clean:
	rm -rf _build *.native
