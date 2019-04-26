# pif

# TODO

figure out how to do Function more nicely (separate builtin/non-builtin types?)

\*list type (entire unnamed _sentence_ context as list, unless sentence context is empty, in which case use unnamed block context - this is really just a hack to make printing nicer)

? allows passing current context without consuming (e.g. for logging/debug etc.)

struct types
  - weakly matched (cf Go's interfaces) for passing
    (BUT type associated - can't mutate things you don't know about, no monkey patching)
  - declaration... ?

clean up base types to act like struct types
  - add some functions to them

[] grouping and associated types:
  [x=1 y=2] -> it's a structy thing (also can stick type in front of to assert). Commas optional
  [x, y,] -> it's a list. Commas required to avoid ambiguity.
  ['x':1; 'y':2;] -> it's a dict (single instruction on LHS to avoid ambiguity, semi-colon to avoid
                                  confusing with list and select operators below)

  -> syntax for copying and deleting?
  -> can also assert type on creation:
     e.g. [Animal Bear Creature|legs=4 colour=brown]

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

- elif

- for loops

- comments

- one line functions (maybe some kind of lookahead but don't process... possible in textx)

- reconsider do/end vs indentation...

- actually making it real: cleaner errors <-> testing <-> reconsider textx...

- make expression do strings and type based lookups. Or even just any single instruction,
  and _call_ functions/resolve types until we get to primitives...

- split int/float?


# How stupid OO looks

Animal = (
  name string
  type string

  show Function
)

Then:

NewBear = func (name string)
  [Animal|
    name = name
    type = "bear"

    show = func (a Animal)
      print ::name " the " ::type " says: ROAR!" .
    end
  ]
end

