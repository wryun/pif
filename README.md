# pif

Sometime you get a stupid idea, and it just won't let you go...

pif is a computer language with two influences from human language
that I haven't seen used in this way before:

- the ability to have a number of unnamed (or potentially named) things
  that one automatically refers to (cf Forth's stack, or Perl's $\_), but
  we use types to determine which one we should use.
- vertically significant whitespace (horizontal significance is so 90s).

This is mostly a joke, and I've so far implemented it with as little effort as
possible (Python! PEG! Performance that will horrify you!). It's a work
in progress; the key primary missing feature is user-definable types (i.e. structs).

All of it really comes from the idea that human language relies on context,
but computer languages generally avoid potential ambiguity. But how far
could we push the ambiguity while remaining sane? So, in pif:

- each sentence has a function/verb (in any position)
- each line (of one or more sentences) has at most one result (either named or not named)
- each paragraph (newline separated) has at most one outstanding unnamed result
  from its lines
- verbs/functions can refer to anything in the context by their types
  (e.g. if I have a function that takes a number, and there is one number
  in the context, I must be referring to that number!)
- unless an unnamed result is the conclusion of a paragraph, you can only
  refer to it once

## Show me some code that doesn't yet work

    Animal = (
      name string
      type string

      talk Function
    )

    NewBear = func (name string) Animal
      [
        name = name
        type = "bear"

        talk = func (Animal)
          print name " the " type " says: ROAR!"
        end
      ]
    end

    NewBear "grumpy" . talk .

So far, so boring. BUT you could also write the final line as:

    "grumpy" NewBear.
    talk.

Here we see there is no ordering to the function arguments.
The `talk` is particularly magical: look in the current context for a struct
that has `talk` as part of it, and find the result of that. Now this would usually consume
the `Animal` (as you can't have multiple references to the same value unless you
name it or it's the final result of a paragraph), but because it's a function we automatically
pass its associated object if it's called.

So this would also be valid:

    NewBear "grumpy" .
    print_s "I created a bear!" .
    # The bear is the only output from this paragraph, and lands
    # in the context.

    talk. # the bear is the only thing in the context that can talk.
    talk. # Because it's the result of a paragraph, we can talk twice.

But this wouldn't be:

    "grumpy" NewBear.
    talk.
    talk. # no bear left to talk - we used him up!

If we wanted the bear to talk twice in the same paragraph,
we'd have to name him properly:

    bear = "grumpy" NewBear.
    bear talk.
    bear talk.

Or, to make things clearer with a little more punctuation:

    bear = "grumpy" NewBear.
    bear::talk.
    bear::talk.

But we don't let ambiguity get completely out of control, so this would fail:

    "grumpy" NewBear.
    "happy" NewBear.
    talk. # fails here - both objects in our context have the talk field.

And so would this:

    NewBear "grumpy" . "happy" NewBear.
    # fails here - two 'results' from above sentence.

And finally:

    1
    "happy"

    # fails here - two results from above paragraph (yes, it's fine to have a line
    # that does not have a function execution at all).

Think of function evaluation as requiring a certain number of arguments. Once
all those arguments are unambiguously filled from the context, it's evaluated.
`print` takes an arbitrary number of arguments, so it's not unambiguously
filled until the end of the line (or a '.' happens, which forces resolution).

## Resolution rules

As introduced in the previous section, _pif_ relies heavily on rules to
determine what a particular identifier or argument refers to.

Almost all of these rules have the possibility of an ambiguous reference,
which is an error if it occurs.

### Unnamed argument resolution (populating function args)

Break if any ambiguity.

- does it exist in the fields of any object in the current context?
- does it exist in the fields of an object in the sentence 

### Named argument resolution

### Named variable resolution

Break if any ambiguity.

- Does it exist in the fields of the object that was just pushed into the context
  in the current sentence?

      NewBear "grumpy" talk

- Does it exist in the fields of an object in the sentence

## Misc contradictory TODO thoughts

Write proper Context tests. Fix up TypeContext to work for
args/args_dupe_types (and write tests for it...)

User accessible 'debug' of current context

do we really want the non-punctuation version? Probably not?
If so, need a way to get a non-greedy function (i.e. one that won't eval)

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
