# pif

Sometime you get a stupid idea, and it just won't let you go...

pif is a computer language with two inspiration from human language
that I haven't seen used in this way before:

- the ability to have a number of unnamed (or potentially named) things
  that one automatically refers to (cf Forth's stack, or Perl's $\_), but
  we use static types to determine which one we should use.
- vertically significant whitespace (horizontal significance is so 90s).

This is mostly a joke, and I've so far implemented it with as little effort as
possible (Python! PEG! Performance that will horrify you!). It's a work
in progress; the key primary missing feature is user-definable types (i.e. structs).

All of it really comes from the idea that human language relies on context,
but computer languages generally avoid potential ambiguity. But how far
could we push the ambiguity while remaining sane? So, in pif:

- each sentence has a function/verb (in any position) and ends in a period
- each line has at most one result (either named or not named)
- each paragraph (newline separated) has at most one outstanding unnamed result
  from its lines
- verbs/functions can refer to anything in the context by their types
  (e.g. if I have a function that takes a number, and there is one number
  in the context, I must be referring to that number!)

## Show me some code that doesn't yet work

    Animal = (
      name string
      type string

      talk Function
    )

    NewBear = func (name string)
      Animal[
        name = name
        type = "bear"

        talk = func (a Animal)
          print a::name " the " a::type " says: ROAR!" .
        end
      ]
    end

    NewBear "grumpy" . ::talk .

So far, so boring. BUT you could also write the final line as:

    "grumpy" NewBear.

    ::talk.

There is no ordering to the function arguments. The period ('`.`') is actually an
instruction that says 'look in the current context, and see if you can find
a function to execute', and when that function is executed it looks around for
arguments in the context that will match. The final ::talk is particularly
magical: look in the current context for a struct that has 'talk' as part of it,
and find the result of that. Now this would usually consume that value
(you usually can't have multiple references to the same value unless you
name it), but because the period is right next to the ::talk we know
what the period is connected to and allow the Animal to be populated
as part of the context.

So this would also be valid:

    "grumpy" NewBear.
    print_s "I created a bear!" .
    # The bear is the only output from this paragraph, and lands
    # in the context.

    ::talk.  # the bear is the only thing in the context that can talk.

But this wouldn't be:

    "grumpy" NewBear.
    ::talk.
    ::talk.  # no bear left to talk - we used him up!

If we wanted the bear to talk twice, we'd have to name him properly:

    grumpy = "grumpy" NewBear.
    grumpy::talk. grumpy::talk.

But we don't let ambiguity get completely out of control, so this would fail:

    "grumpy" NewBear.
    "happy" NewBear.
    ::talk.  # fails here - both objects in our context can talk.

And so would this:

    "grumpy" NewBear. "happy" NewBear.
    # fails here - two 'results' from above sentence.

And finally:

    1
    "happy"

    # fails here - two results from above paragraph (yes, it's fine to have a line
    # that does not have a function execution at all).

## Misc contradictory TODO thoughts

some way to explicitly pull something out of current context? Or is this just misunderstanding?
  (in REPL, would be nice to generate _then_ assign - and also to discard with `_`)

REPL - need to recover from error situation caused by throwing different types into
  current context (causes subsequent errors)
  --- also, should support different types in current context...

any

type equality/isinstance comparisons

figure out how to do Function more nicely (separate builtin/non-builtin types?)

add proper boolean support

\*list type (entire unnamed _sentence_ context as list, unless sentence context is empty, in which case use unnamed block context - this is really just a hack to make printing nicer)

? allows passing current context without consuming (e.g. for logging/debug etc.)

struct types
  - weakly matched (cf Go's interfaces) for passing
    (BUT type associated - can't mutate things you don't know about, no monkey patching)
  - OTOH, how does this work with multiple things in context rules? post-facto?
  - declaration... ?

zig style fake generics?

clean up base types to act like struct types
  - add some functions to them

[] grouping and associated types:
  [x=1 y=2] -> it's a structy thing (also can stick type in front of to assert). Commas optional
  [x, y,] -> it's a list. Commas required to avoid ambiguity.
  ['x':1; 'y':2;] -> it's a dict (single instruction on LHS to avoid ambiguity, semi-colon to avoid
                                  confusing with list and select operators below)

  -> syntax for copying and deleting?
  -> can also assert type on creation:
     e.g. [Animal Bear Creature|legs=4 colour="brown"]

: select one of
  [x=1 y=2]::x
  [x y]:0
  ['x':1 'y':2]:'y'

  -> also should support interesting things like [x=1] 2 ::x (i.e. find something we can get ::x out of)
     structs with ':' alone support dict style lookups (:: is a symbol thing)
  -> difference between structs and dicts is that structs are fixed in terms of named things
  -> however, if it's function on a struct, curry it... somehow (OO-lite). Lightweight but confusing
     would be just to place the struct in the current context as well. Won't work for things like
     1 2::add (which would place two numbers into context, etc. etc.)

* destructuring:
  \*[1 "a"] -> throw everything into sentence context as types (i.e. will fail if dupes!)
  \*[x=1 y="a"] -> throw everything into sentence context with names (allows override)

- one line functions (maybe some kind of lookahead but don't process... possible in textx)

- reconsider do/end vs indentation...

- actually making it real: cleaner errors <-> testing <-> reconsider textx...
  (STACKTRACES!)

- make expression do strings and type based lookups. Or even just any single instruction,
  and _call_ functions/resolve types until we get to primitives...

- split int/float?
