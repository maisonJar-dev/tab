# The trefoil knot

The **trefoil** is the simplest knot there is. It looks like a pretzel, or three overlapping
loops, but behind that simple shape sits an entire branch of mathematics, with links to
biology, physics and computer science.

## What a mathematician means by "knot"

Take a piece of string, tie it in a knot, then **glue the two ends together**. That's a
mathematical knot: a closed loop in three-dimensional space that never passes through itself.

Gluing the ends matters. A knot in a shoelace can always be undone by pulling an end back
through. Once the ends are joined there's no end to pull, so a knotted loop stays knotted
however you bend, stretch or twist it. The only way out is to cut it.

The simplest loop is a plain circle, which mathematicians call the **unknot**. The big
question of knot theory sounds simple:

> Given two tangled loops, can one be moved into the other without cutting?

The trefoil is the first loop that can't be turned into the unknot. Nothing with fewer
crossings is knotted at all. With three crossings it's the most basic knot there is.

## Proving it's really knotted

Saying the trefoil can't be untangled is easy. *Proving* it is harder. You can't try every
possible wiggle, because there are infinitely many. Mathematicians use **invariants**
instead: properties that stay the same however you move the loop. If two loops differ in an
invariant, they must be different knots.

The prettiest invariant is **tricolourability**. Draw the knot flat, with a small break
wherever one strand passes under another. Each unbroken piece
is a *strand*. Now try to colour the strands using three colours, following two rules:

1. At every crossing, the three strands that meet are **all the same colour or all
   different**.
2. You use **at least two** colours.

The trefoil can do it: give each of its three strands its own colour, and every crossing has
all three. The unknot can't. A circle drawn with no crossings has just one strand, so it
only ever gets one colour.

The clever part, proven using **Reidemeister moves**, is that this property survives every
possible way of moving the loop. Kurt Reidemeister showed in 1927 that any movement of a knot
can be broken down into three small local moves on its drawing: adding or removing a twist,
sliding one strand over another, and sliding a strand past a crossing. Check that each move
keeps a valid colouring valid and you've checked every movement at once. So the trefoil is
tricolourable, the unknot isn't, and they can't be the same knot. Pure logic, no wiggling.

## It has a handedness

Hold the trefoil up to a mirror and you get a second trefoil, twisting the other way. A
left-handed and a right-handed trefoil look alike, but **no amount of moving turns one into
the other**, just as no rotation turns your left hand into your right. Max Dehn proved this
in 1914.

You can turn a trefoil through every angle in space and it stays the same hand. Turning it
can never flip it into its mirror image. Many knots behave like this, but not all: the
figure-eight knot, the next simplest, can be moved into its own mirror image.

## Where the shape comes from

The trefoil can be written down with three short formulas. As *t* goes once around a
circle, the point

- x = sin *t* + 2 sin 2*t*
- y = cos *t* − 2 cos 2*t*
- z = −sin 3*t*

traces the trefoil in 3D. The *z* part, rising and falling three times, lifts one strand over
another at each crossing.

It's also a **torus knot**: picture a doughnut and wind a string around it so it goes around
the hole twice while looping through it three times. Close the loop and you've drawn a
trefoil. Every pair of whole numbers with no common factor gives a torus knot this way, and
(2, 3) is the smallest one that's really knotted.

## Born from a wrong theory of atoms

Knot theory began with a mistake. In the 1860s Lord Kelvin suggested that atoms were tiny
knotted whirlpools in the "aether" that was then thought to fill space, and that each chemical
element was a different knot. If that were true, a table of knots would be a periodic table.

So the physicist Peter Guthrie Tait, with Thomas Kirkman and Charles Little, spent years
drawing up tables of every knot by its number of crossings. The aether turned out not to
exist and Kelvin's atoms were dropped, but the tables survived and became the start of a new
branch of mathematics.

They were also hard to get right. In 1974 Kenneth Perko, a lawyer who studied knots as a
hobby, showed that two knots listed separately in Little's table for almost a century were
really the same knot. The pair is still called the **Perko pair**.

## How fast knots multiply

The number of different knots (counting only "prime" ones, not knots tied one after another
on the same loop) grows fast with the number of crossings:

- 3 crossings: 1 (the trefoil)
- 4 crossings: 1 (the figure-eight knot)
- 5 crossings: 2
- 6 crossings: 3
- 7 crossings: 7
- 8 crossings: 21
- 9 crossings: 49
- 10 crossings: 165

By 16 crossings there are well over a million. The trefoil sits alone at the start.

## Why it matters beyond maths

**Biology.** DNA is a very long strand packed into a tiny nucleus, and it gets tangled and
knotted. Cells make enzymes called *topoisomerases* that cut a strand, pass another through
the gap and reseal it: a real-life version of "the only way out is to cut it". Some
antibiotics and cancer drugs work by jamming these enzymes. Biologists also use knot theory
to work out how the enzymes act from the knots they leave behind. Some proteins even fold
into knots, the trefoil being the most common.

**Physics.** In 1984 Vaughan Jones found a new invariant, the **Jones polynomial**. For one
trefoil it's *t* + *t*³ − *t*⁴, and for its mirror image you swap *t* for 1/*t*. The two
results differ, which is another proof that the two hands are different knots. Edward Witten
then showed that the Jones polynomial comes out of quantum field theory, the language of
particle physics. Both won the Fields Medal, maths' highest honour, in 1990. The same ideas
feed into **topological quantum computing**, where information would be stored in how
particle paths braid around each other, which is very hard for noise to disturb.

**Computer science.** Can a computer tell whether a tangled loop is really just the unknot?
Joel Hass, Jeffrey Lagarias and Nicholas Pippenger showed in 1999 that the problem is
solvable and that a "yes" can be checked quickly, which puts it in the class NP. Whether it
can be *solved* quickly is still open. In 2021 Marc Lackenby announced an algorithm close to
polynomial time. A question that sounds like a children's puzzle sits right at the edge of
what we know how to compute.

## Still unsolved

For all its simple look, knot theory is full of open questions. No one knows whether the
Jones polynomial can always tell the unknot apart from real knots: every knot checked so far
gets a different polynomial from the unknot, but there's no proof that it always will. The
**unknotting number**, the fewest times you'd have to let a knot pass through itself to undo
it, is known to be 1 for the trefoil but is still unknown for some knots with only ten
crossings.

That's what makes the trefoil remarkable. It's the first knot anyone meets, a three-crossing
loop you can tie in a few seconds, and it leads straight to questions that mathematicians
still can't answer.
