let main () =
  Lexer.init ();
  let lexbuf = Lexing.from_channel stdin in
  let phrases = Parse.use_file lexbuf in
  List.iter (fun phrase ->
    let open Parsetree in
    (match phrase with
       | Ptop_def structure ->
         List.iter (fun item ->
           (match item.pstr_desc with
            | Pstr_eval (expr, attr) -> () (* Printf.printf "%s\n" (Pprintast.string_of_expression expr) *)
            | Pstr_value (_, vals) ->
              (match (List.hd vals).pvb_expr.pexp_desc with
              | Pexp_fun _ ->
                Pprintast.toplevel_phrase Format.str_formatter phrase;
                Printf.printf "%s\n" (Format.flush_str_formatter ())
              | _ -> ())
            | _ -> ()))
           structure
       | _ -> ()))
    phrases

let () = main ()
