**Misc/Golf?**

**Challenge**

Produce a number spiral while staying within a strict rendered pixel-width limit.

**Solution**

The server asks for Python code that prints a 10×10 clockwise number spiral.

The trick is that the code is not limited by character count. It is rendered using DejaVu Sans, and its total pixel width must stay below 380px:

```python
if font.getlength(code) > 380:
    return "TOO LONG"
```

Because the font is proportional, narrow names such as `i`, `j`, and `l` are much cheaper than wider characters. This also makes symbols such as `=` and `+` surprisingly expensive.

Instead of generating the spiral with four directional loops, we can build it from the inside out. Each round adds a new row and rotates the existing matrix clockwise:

```python
l=[[]];i=100
while i:j=i;i-=len(l);l=[range(i,j),*zip(*l[::-1])]
for j in l:print(*j)
```

Starting with `[[]]` naturally produces row lengths of `1, 1, 2, 2, ... 9, 9, 10`, using every number from 0 to 99.

The final code measures about 376.97px, just under the 380px limit, and prints the correct spiral.

**Flag**

**scriptCTF{8u7_1_c@n7_s3e_7h3_c0d3}**

## Reasoning Process

I first separated the mathematical requirement from the unusual scoring rule. The output had to be exact, but the submission was constrained by rendered width rather than source length. That changed the optimization target: identifiers made of narrow glyphs were preferable even when they used the same number of characters.

The inside-out construction avoids maintaining four boundaries and directions. At each iteration, `range(i,j)` creates the next outer row while `zip(*l[::-1])` rotates the previous matrix. I verified the candidate locally against the reference 10×10 spiral and measured it with the same DejaVu Sans font used by the server. The final 376.97 px result leaves only a small margin below the 380 px limit, so matching the server's font and version is important for reproducibility.
